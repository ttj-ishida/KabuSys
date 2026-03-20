CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。
このプロジェクトはセマンティックバージョニングを使用します。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-20
-------------------

Added
- 初期リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ のエクスポートを追加。

- 環境・設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を追加。プロジェクトルートは .git または pyproject.toml を起点に探索。
    - .env 行のパースロジックを実装（コメント／export 形式／クォート／エスケープ対応）。
    - .env 読み込み時の上書き制御（override / protected）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - Settings クラスを実装し、J-Quants / kabu / Slack / DB パス / 環境名 / ログレベル等のプロパティを提供。値検証（有効な env / log level の検査、必須変数チェック）を行う。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
    - レート制御（固定間隔スロットリング）を実装する RateLimiter を導入（120 req/min）。
    - 再試行（指数バックオフ、最大3回）・HTTP 429 の Retry-After 処理・401 時のトークン自動リフレッシュ（1回のみ）を実装。
    - ID トークンのモジュールレベルキャッシュを実装。
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を追加。ON CONFLICT を用いた更新、fetched_at（UTC）を記録。
    - 入力データ変換ユーティリティ _to_float, _to_int を実装（堅牢な変換と欠損扱い）。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集・正規化して raw_news に保存する基盤を追加。
    - URL 正規化（トラッキングパラメータ除去・クエリソート・フラグメント削除）、コンテンツ正規化、記事ID のSHA-256 ベース生成戦略を設計（冪等性確保）。
    - セキュリティ対策: defusedxml を用いた XML パース、受信最大バイト数制限、SSRF やトラッキングパラメータ対策等を仕様として明記。
    - 大量挿入へ対応するチャンク化処理。

- リサーチ（ファクター計算・探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（calc_momentum）、ボラティリティ／流動性（calc_volatility）、バリュー（calc_value）の各ファクター計算を実装。prices_daily / raw_financials を参照して日付単位で結果を返す。
    - 移動平均・ATR・出来高平均などのウィンドウ集計を SQL（DuckDB）ベースで実装。データ不足時は None を返す挙動を明確化。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応）、IC（Spearman）計算 calc_ic、統計サマリー factor_summary、ランク化ユーティリティ rank を実装。
    - Pandas 等に依存せず標準ライブラリ＋DuckDB で完結する設計。
  - src/kabusys/research/__init__.py
    - 上記関数群と zscore_normalize を公開。

- 戦略（特徴量生成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - build_features を実装。research モジュールの生ファクターをマージし、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（zscore_normalize）、±3 クリップを行った上で features テーブルへ日付単位で置換（トランザクションで原子性）する処理を提供。
  - src/kabusys/strategy/signal_generator.py
    - generate_signals を実装。features と ai_scores を組み合わせ、コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算して final_score を算出。
    - 重みの補完と正規化、weights の入力検証（負値/NaN/Inf/未知キーの無視）を搭載。
    - Bear レジーム判定（AI の regime_score の平均が負かつサンプル数閾値以上）により BUY を抑制。
    - BUY閾値による買いシグナル生成、保有ポジションに対するエグジット判定（ストップロス、スコア低下）に基づく SELL シグナル生成を実装。
    - signals テーブルへ日付単位の置換をトランザクションで実施し冪等性を保証。

- パッケージ構成
  - src/kabusys/strategy/__init__.py で build_features / generate_signals をエクスポート。
  - 空の execution パッケージ（src/kabusys/execution/__init__.py）を用意（将来の発注層を想定）。

Changed / Improved（堅牢性・ログ等）
- 多くの計算において math.isfinite や None チェックを導入し、欠損値や無限値による誤計算を抑制。
- DB 書き込み周りはトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保。ROLLBACK に失敗した場合の警告ログ出力を追加。
- fetch/save 系で PK 欠損行はスキップし、スキップ数を警告ログに出力。
- API 呼び出しでの 429 処理は Retry-After ヘッダを優先して待機する実装を追加。
- generate_signals: weights の合計が 0 の場合はデフォルト重みにフォールバックする安全措置を追加。
- SELL 判定で価格欠損時は判定をスキップして意図しないクローズを防止するロギングを追加。

Fixed（設計上の注意・既知の未実装）
- positions テーブル側の情報不足（peak_price / entry_date 等）があるため、トレーリングストップ・時間決済など一部エグジット条件は未実装として明記。
- calc_ic は有効レコード数が 3 未満の場合は計算不能として None を返すようにして誤解を防止。
- get_id_token の内部呼び出しで無限再帰することのないよう allow_refresh フラグを導入している。

Security
- news_collector で defusedxml を利用し XML 関連の脆弱性（XML Bomb 等）を回避する方針を採用。
- RSS の受信サイズ上限を設け、URL 正規化でトラッキングパラメータを削除することでトラッキング付与によるノイズを低減。
- J-Quants クライアントは Authorization ヘッダの取扱いとトークン自動更新を慎重に扱う設計。

Known issues / Limitations
- execution（発注）層は未実装。signal -> 実際の発注は別実装が必要。
- 一部アルゴリズム（トレーリングストップ、時間決済）は positions 側の追加情報がないため未実装。
- news の記事から銘柄マッチング（news_symbols との紐付け）や AI ニューススコア生成は外部処理や別モジュール依存を想定している（本リリースでは ai_scores を入力として利用するのみ）。

Acknowledgements
- 本リリースは DuckDB をデータ処理基盤として利用する前提で設計されています。
- 設計説明（StrategyModel.md / DataPlatform.md 等）に基づいた実装方針をコード内コメントで明記しています。

-----

将来的には execution 層の実装、ニュース→AI スコア変換パイプライン、さらに監視・運用（monitoring）周りの充実を予定しています。フィードバックや改善提案があればお知らせください。