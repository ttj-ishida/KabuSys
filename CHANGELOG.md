Keep a Changelog 準拠の形式で、コードベースから推測した変更履歴を以下に記載します。

CHANGELOG.md
=============

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に従い、セマンティックバージョニングを採用します。

v0.1.0 - 2026-03-21
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - Python パッケージのエントリポイントを定義
    - src/kabusys/__init__.py に __version__ = "0.1.0"、公開モジュール一覧を設定。
  - 設定管理
    - src/kabusys/config.py
      - .env/.env.local からの自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索）。
      - 行パーサー実装（コメント・export 形式・クォート・エスケープ対応）。
      - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。
      - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - Settings クラスでアプリ設定プロパティを提供（J-Quants トークン、kabu API、Slack、DB パス、環境 / ログレベル判定など）。
      - 必須環境変数未設定時に ValueError を送出する _require ユーティリティ。
  - Data レイヤー
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアント実装（データ取得・ページネーション対応）。
      - 固定間隔レートリミッタ実装（120 req/min）。
      - リトライ（指数バックオフ最大 3 回）・HTTP エラー処理（408/429/5xx 対象）・429 の Retry-After 対応。
      - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
      - fetch_* 系で日足 / 財務 / 市場カレンダーの取得実装。
      - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE を使用）。fetched_at に UTC 時刻を記録。
      - 値変換ユーティリティ (_to_float, _to_int) による安全なパース。
    - src/kabusys/data/news_collector.py
      - RSS 収集モジュール（RSS パース、URL 正規化、トラッキングパラメータ除去、記事 ID の SHA-256 ハッシュ化方針）。
      - セキュリティ対策（defusedxml の使用、受信サイズ上限、SSRF 対策方針の明示）。
      - raw_news への冪等保存を想定した設計（バルク挿入・チャンク化）。
  - Research レイヤー
    - src/kabusys/research/factor_research.py
      - Momentum, Volatility, Value 系ファクター計算を実装。
        - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（MA200 の行数チェックあり）。
        - calc_volatility: ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio（真のレンジ計算時の NULL 伝播制御）。
        - calc_value: raw_financials と価格を組み合わせた per / roe（report_date <= target_date の最新財務データを取得）。
      - DuckDB を用いた SQL + ウィンドウ関数中心の実装で営業日欠損やウィンドウ不足に対処。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン取得（LEAD を使用、ホライズン検査あり）。
      - calc_ic: スピアマンランク相関（Information Coefficient）実装（同値処理・最小サンプル検査）。
      - factor_summary: 基本統計量（count/mean/std/min/max/median）計算。
      - rank: 平均ランク（同順位は平均ランク）実装（丸めによる ties 検出安定化）。
    - research パッケージの公開 API を __init__ で整備。
  - Strategy レイヤー
    - src/kabusys/strategy/feature_engineering.py
      - build_features: research の生ファクターを統合し、ユニバースフィルタ（最低株価・最低売買代金）適用、Z スコア正規化（カラム指定）、±3 でクリップ、features テーブルへ日付単位で UPSERT（トランザクションで原子性保証）。
      - ルックアヘッドバイアス対策（target_date 時点のデータのみ使用）。
    - src/kabusys/strategy/signal_generator.py
      - generate_signals: features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算で final_score を作成し BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換。
      - デフォルト重みと閾値（momentum 0.40 等、threshold 0.60）を定義。ユーザ指定 weights は検証・再スケール処理を行う。
      - Sigmoid 変換・欠損値は中立値 0.5 で補完する方針。
      - Bear レジーム判定（ai_scores の regime_score 平均が負で且つ十分なサンプル数がある場合 BUY を抑制）。
      - SELL 判定ロジック（ストップロス -8% 優先、スコア低下）。既知の未実装条件（トレーリングストップ、時間決済）をコメントで明示。
      - ポジション・価格取得は DuckDB から行い、価格欠損時は SELL 判定をスキップして誤クローズを防止。
  - パッケージモジュール公開
    - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
    - src/kabusys/research/__init__.py で研究系のユーティリティ群を公開。

Changed
- 初回リリースのため、従来との互換性変更なし（初版）。

Fixed
- 初回リリースのため、バグ修正履歴なし（初版）。

Known limitations / Notes
- signal_generator の SELL 判定において、トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date 等の情報が必要）。
- calc_value は PBR・配当利回りの計算を現バージョンでは未実装。
- news_collector モジュールは設計上のセキュリティ方針や正規化処理を備えるが、実運用での接続先増加やマルチソースの細かなルールは追加が必要になる可能性あり。
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DB パス等は DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
  - 実行環境指定 KABUSYS_ENV（development|paper_trading|live）、ログレベル LOG_LEVEL（DEBUG/INFO/...）
- .env パーサーは多くのケースに対応するが、極端に複雑なシェル式（改行を含むクォート、複雑なエスケープ）などのパーシング差異は注意が必要。

導入 / 移行メモ
- .env / .env.local をプロジェクトルートに配置すると自動で読み込まれる（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- DuckDB スキーマ（raw_prices, raw_financials, market_calendar, features, ai_scores, signals, positions 等）はコードの SQL と整合するよう事前に作成すること。
- J-Quants API を使用するには JQUANTS_REFRESH_TOKEN のセットが必要。get_id_token() が自動でトークンを取得する。

参考
- 主要な設計上の方針として、ルックアヘッドバイアス防止・冪等性（DB の ON CONFLICT / 日付単位の置換）・トランザクション原子性・外部サービスへの安全なアクセス（リトライ・レート制限・セキュリティ対策）が慎重に考慮されています。

（以降のバージョンでは、未実装条件の実装、ニュース抽出の強化、monitoring/ execution 層の実装・テスト充実化、カバレッジと運用監視の追加等を予定しています。）