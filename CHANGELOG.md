# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従って記載しています。

## [0.1.0] - 2026-04-09

Initial release — 日本株自動売買支援ライブラリ "KabuSys" の初期実装を追加。

### 追加 (Added)
- 基本パッケージ公開
  - src/kabusys/__init__.py
    - パッケージのメタ情報と公開モジュール一覧を定義（data, strategy, execution, monitoring）。
    - バージョン: 0.1.0

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイルや環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパース機能を独自実装（`export KEY=val` 対応、引用符・エスケープ、インラインコメント処理）。
    - 設定アクセス用の Settings クラスを提供（プロパティ経由で以下を取得）:
      - J-Quants / kabu ステーション / LINE / データベースパス（DuckDB/SQLite） / Paper Trading 設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH） / 監視関連（PID/kill flag, リソース閾値） / システム設定（KABUSYS_ENV, LOG_LEVEL, is_live/is_paper/is_dev）
    - 複数の入力値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を実装し、不正値は ValueError を送出。

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/__init__.py
    - news_nlp.score_news を公開。

  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（DB 比較は UTC naive datetime）。
    - バッチ処理: 最大 20 銘柄/コール、1銘柄あたり最大 10 記事・3000 文字までトリム。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対し指数バックオフでリトライ（最大 _MAX_RETRIES）。
    - レスポンス検証: JSON の抽出・構造チェック・スコアの数値性検証・既知コードのみ採用。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして他の銘柄処理を継続。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）について 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等的に書き込む機能を実装。
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウ抽出、マクロキーワードによるタイトル抽出後 OpenAI でセンチメント評価（gpt-4o-mini）。
    - API 呼び出しのリトライ/バックオフ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッド防止の設計（date 引数ベース、DB クエリは target_date 未満限定）。
    - テスト用フック: _call_openai_api を差し替え可能。

- データ処理（Data Platform）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーを管理するマーケットカレンダー関連ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB データ（market_calendar）が無い場合は曜日ベース（週末除外）のフォールバックを採用。
    - 夜間バッチ更新 calendar_update_job を実装し、J-Quants から差分取得 → idempotent に保存（fetch/save は jquants_client に委譲）。
    - バックフィル（直近 _BACKFILL_DAYS の再取得）、健全性チェック（最大未来日数）のロジックを実装。

  - src/kabusys/data/pipeline.py & src/kabusys/data/etl.py
    - ETL 用の ETLResult データクラスを提供（etl.py では pipeline.ETLResult を再エクスポート）。
    - ETL パイプラインの設計方針と定数（差分更新、バックフィル、品質チェック、J-Quants データの最小開始日など）を定義。
    - ETLResult に品質問題・エラーメッセージの集約、辞書化ユーティリティを実装。

  - src/kabusys/data/__init__.py
    - data サブパッケージ（内部モジュール群）のプレースホルダ（公開は pipeline.ETLResult を通じて行われる）。

- 研究（Research）モジュール
  - src/kabusys/research/__init__.py
    - 研究用ユーティリティの公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

  - src/kabusys/research/factor_research.py
    - モメンタム / ボラティリティ / バリュー等の定量ファクターを DuckDB 上の SQL と Python 組合せで計算する関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離など。
      - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率など。
      - calc_value: raw_financials から最新の EPS/ROE を取得して PER/ROE を計算（EPS が 0 や欠損の場合は None）。
    - 設計: DuckDB の prices_daily / raw_financials のみ参照、外部 API にはアクセスしない。結果は (date, code) をキーとする dict のリストで返す。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
    - 入力検証（horizons が正の整数かつ <= 252 等）や、欠損値/有限値の扱いに注意。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

### セキュリティ (Security)
- なし（初回リリース）
  - ただし OpenAI API キー・各種機密は環境変数で管理する設計。Settings._require で必須キーの未設定は ValueError により明示する。

### 実装上の重要な注意点（備考）
- OpenAI 呼び出し:
  - モデル: gpt-4o-mini を想定。JSON Mode を利用する（response_format={"type":"json_object"}）。
  - リトライ・バックオフ戦略とレスポンス検証を実装しており、API 失敗時はフェイルセーフで継続する設計。

- DuckDB テーブル前提:
  - modules が参照する主なテーブル: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等。
  - ai_scores 書き込みは「DELETE (該当 code) → INSERT」の順で行い、部分失敗時に他コードの既存スコアを消さない工夫をしている（DuckDB 互換性のため executemany を使用）。

- ルックアヘッドバイアス対策:
  - 全ての AI/研究処理は datetime.today() / date.today() を内部で参照せず、必ず外部から与えられる target_date を基準に動作する設計。

- テスト容易性:
  - OpenAI 呼び出し箇所は内部関数を経由しており、unittest.mock.patch で差し替えてテスト可能。

- 環境変数の自動ロード:
  - パッケージ配布後も .env 自動検出が正しく動作するよう、__file__ を起点にプロジェクトルートを探索する実装。

もしリリースノートをもっと細かく（ファイル単位の変更差分、対応Issue番号など）記載したい場合は、その情報を提供してください。必要に応じて英語版やセクション分割（Breaking Changes 等）も作成できます。