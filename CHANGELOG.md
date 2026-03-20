Keep a Changelog に準拠した CHANGELOG.md（日本語）

全体方針:
- この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートは運用上の判断や追加情報に応じて調整してください。
- フォーマット: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠

Unreleased
---------
（なし）

0.1.0 - 2026-03-20
-----------------
初回リリース — 基本的なデータ取得・加工・戦略生成パイプラインを実装

Added
- パッケージ基礎
  - kabusys パッケージ初期化 (src/kabusys/__init__.py) とバージョン定義（0.1.0）。
  - strategy, data, execution, monitoring を公開 API に含めるエントリポイントを追加。

- 設定管理
  - 環境変数・設定読み込みモジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml で検出して .env / .env.local を自動読み込みする仕組みを実装。
    - export KEY=val 形式、クォート文字列・エスケープ処理、インラインコメント判定などを考慮した .env パーサを実装。
    - OS 環境変数を保護する protected 機能、override オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境・ログレベル等のプロパティを取得する API を公開。環境値の妥当性チェック（env, log_level）や is_live/is_paper/is_dev ヘルパーを実装。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - API レート制限（120 req/min）を守る固定間隔スロットル RateLimiter を実装。
    - HTTP リクエストの共通処理を提供し、指数バックオフによるリトライ（最大 3 回）を実装。408/429/5xx 等の再試行対象に対応。
    - 401 応答時にリフレッシュトークンから id_token を再取得して 1 回だけリトライする自動リフレッシュ処理を実装。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT で更新）。
    - データ整形ユーティリティ _to_float / _to_int を実装し、不正な形式や空値を安全に扱う。

- ニュース収集
  - RSS ベースのニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - デフォルト RSS ソース定義、受信サイズ制限（10MB）、URL 正規化（トラッキングパラメータ除去・ソート・フラグメント除去）を実装。
    - 記事ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を担保する設計。
    - defusedxml を使用した安全な XML パース（XML Bomb 等の防御）、SSRF の抑制（HTTP/HTTPS チェック）は設計に明示。
    - DB へのバルク挿入チャンク処理とトランザクション方針を記載。

- リサーチ / ファクター計算
  - factor_research モジュールを実装（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20 日 ATR、相対 ATR、出来高系指標）、Value（PER, ROE）など主要ファクターを DuckDB の prices_daily / raw_financials テーブルを用いて計算する関数（calc_momentum / calc_volatility / calc_value）を追加。
    - 窓サイズやスキャンレンジ、欠損時の扱い（データ不足 → None）を明確化。
  - feature_exploration（src/kabusys/research/feature_exploration.py）を追加。
    - 将来リターン計算 calc_forward_returns（複数ホライズンに対応、入力検証あり）。
    - IC（Spearman の ρ）計算 calc_ic、ランク関数 rank、ファクター統計量 summary（factor_summary）を実装。
    - pandas 等外部依存を避け、標準ライブラリ + DuckDB のみで実装する設計方針を採用。
  - research パッケージの __init__ に主要 API を公開。

- 特徴量エンジニアリング
  - feature_engineering モジュールを追加（src/kabusys/strategy/feature_engineering.py）。
    - research の生ファクターを取得（calc_momentum, calc_volatility, calc_value）してマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 特定列について Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ、features テーブルへ日付単位で置換（トランザクション）する build_features を実装。
    - ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）と冪等性を強調。

- シグナル生成（戦略）
  - signal_generator（src/kabusys/strategy/signal_generator.py）を追加。
    - features と ai_scores を統合して各コンポーネント（momentum/value/volatility/liquidity/news）を計算し、重み付け合算で final_score を生成。デフォルト重みと閾値を定義。
    - スコア変換にシグモイド関数と中立値補完（None → 0.5）を採用。
    - Bear レジーム判定（ai_scores の regime_score 平均が負、ただしサンプル数閾値を満たす場合に判定）を実装し、Bear 時に BUY シグナルを抑制。
    - 保有ポジションのエグジット条件（ストップロス -8% / final_score が閾値未満）に基づく SELL シグナル生成を実装（_generate_sell_signals）。トレーリングストップ等は未実装だが設計上明記。
    - signals テーブルへ日付単位の置換（トランザクション）で挿入し、BUY と SELL の優先処理（SELL を除外して BUY をランク付け）を実装。
    - generate_signals は入力 weights の検証・スケーリングを行い、ログ出力を多く含む。

Changed
- （初版のため「Changed」は無し。将来のリリースで差分を記載してください。）

Fixed
- （初版のため「Fixed」は無し。将来のリリースでバグ修正を記載してください。）

Security
- ニュース収集において defusedxml を採用し XML 関連の攻撃を防御する設計を採用。
- ニュース URL 正規化とトラッキングパラメータ除去、HTTP/HTTPS チェックにより SSRF や重複検出を抑制する設計を明示。
- J-Quants クライアントはトークン管理・自動リフレッシュを実装し、認証漏れ時の安全な再試行ロジックを提供。

Notes / Known limitations
- execution パッケージは初期化ファイルのみで実体（発注ラッパー等）は未実装。
- monitoring モジュールの具体実装はソース上に見当たらないため、監視・アラート周りは未実装。
- signal_generator の一部エグジット条件（トレーリングストップ・時間決済）は positions テーブルに追加情報（peak_price / entry_date 等）が必要であり未実装。
- feature_engineering / research の正規化に用いる zscore_normalize は kabusys.data.stats に存在する想定であり、外部実装との整合性を確認する必要あり。
- News collector の詳細な挿入処理（DB スキーマとのマッピングや news_symbols 連携）は実装想定のままコード断片で終了している部分があるため、実運用前に DB スキーマとワークフローを確認すること。

Acknowledgements
- 本 CHANGELOG は提供されたソースコードから機能・設計を推測して作成しました。実運用・リリースノート作成時にはテスト結果や運用上の注意、互換性ポリシー（MAJOR.MINOR.PATCH の運用方針）を追記してください。