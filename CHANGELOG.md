# Changelog

すべての重要な変更点を記載します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-02

初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加内容・設計方針は以下の通りです。

### Added
- パッケージ基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (`kabusys.config`)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で利用可）。
  - .env のパース実装を強化:
    - export プレフィックス対応（`export KEY=val`）。
    - シングル/ダブルクォート内のバックスラッシュエスケープと閉じクォート検出対応。
    - 非クォート値でのインラインコメント（`#`）扱いを文脈依存で処理。
  - `_load_env_file` による OS 環境変数保護（protected set）と override 制御を実装。
  - Settings クラスを導入し、J-Quants / kabu / Slack / DB / 監視 / システム関連の設定プロパティを提供（必須設定は _require で ValueError を投げる）。
  - `env` / `log_level` に入力検証を行い、不正値は ValueError を送出。

- AI 関連 (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.py`)
    - raw_news と news_symbols を集約して OpenAI (gpt-4o-mini) による銘柄別センチメントスコアを取得し、ai_scores テーブルへ書き込む `score_news` を実装。
    - JSTベースのニュース収集ウィンドウ計算関数 `calc_news_window` を実装（前日 15:00 JST 〜 当日 08:30 JST を対象）。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、各銘柄ごとに最大記事数・文字数制限を導入してトークン肥大化を回避。
    - レスポンスのバリデーション・スコアクリップ（±1.0）を実装。
    - OpenAI API 呼び出しでの 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによる再試行を実装。
    - テスト容易性のため `_call_openai_api` を分離してモック差し替えを想定。
    - 部分失敗時に既存スコアを保護するため、書き込みは該当コードのみの DELETE → INSERT の置換を行う（DuckDB の executemany の制約に注意）。
  - 市場レジーム判定 (`regime_detector.py`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する `score_regime` を実装。
    - マクロニュース取得は `news_nlp.calc_news_window` を利用してウィンドウ内のタイトルを抽出し、OpenAI に JSON 出力でスコアを要求して集約。
    - API 失敗時は macro_sentiment=0.0 を採用するフェイルセーフ動作。
    - レジームスコア計算後に market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。失敗時は ROLLBACK を試みる。
    - OpenAI 呼び出し用のクライアント呼び出し部分は `news_nlp` と意図的に別実装としてモジュール結合を低減。

- データ基盤 (`kabusys.data`)
  - ETL パイプライン基盤 (`pipeline.py`)
    - DataPlatform に基づく差分取得・保存・品質チェック設計を実装するための基盤を用意。
    - ETL 実行結果を表現する `ETLResult` dataclass を追加（品質問題・エラーの集約、辞書化メソッドを提供）。
    - テーブル存在チェックや最大日付取得などのユーティリティを実装（DuckDB 前提）。
  - ETL 公開インターフェース (`etl.py`)
    - pipeline の `ETLResult` を再エクスポート。
  - マーケットカレンダー管理 (`calendar_management.py`)
    - JPX カレンダーを扱う夜間バッチ `calendar_update_job` を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存）。
    - 営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB にデータが無い場合は曜日ベースでフォールバック。
    - 最大探索日数制限や各種フォールバックの一貫性を確保。
    - jquants_client（`kabusys.data.jquants_client`）を利用して取得・保存処理を分離。

- リサーチ / ファクター系 (`kabusys.research`)
  - ファクター計算 (`factor_research.py`)
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）を計算する関数群を実装（calc_momentum / calc_value / calc_volatility）。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのラグ・移動平均を計算。
    - データ不足時は None を返す設計。
  - 特徴量探索 (`feature_exploration.py`)
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンのリターンを一度のクエリで取得。horizons の入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: factor と forward をコードで結合し、スピアマンのランク相関を算出。無効レコード・小サンプル時の処理を実装。
    - ランク関数（rank）: 同順位は平均ランクを割り当て、丸めで ties を検出する実装。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - research パッケージの公開 API を __init__ で整理。

### Changed
- 設計方針（全体）
  - ルックアヘッドバイアス防止のため、いかなる場所でも datetime.today() / date.today() を直接参照しないよう意識した実装（target_date を引数に取る設計を徹底）。
  - OpenAI など外部 API の失敗はフェイルセーフ（例: スコア 0.0 やスキップ）で継続する戦略を採用し、ETL/解析の頑健性を向上。

### Fixed
- トランザクション保護とロールバック
  - AI スコア / レジーム書き込み / ETL のテーブル更新等で、例外発生時に ROLLBACK を試み、ROLLBACK 自体の失敗は警告ログに留める実装を追加（例外の上位伝播を維持）。

### Security
- 環境変数の取り扱いを明確化
  - API キー類（OpenAI, Slack, J-Quants, kabu API）取得箇所で未設定時は明確に ValueError を発生させ、秘密情報の欠落を早期検出。

### Notes / Breaking Changes / Migration
- AI 機能 (`score_news`, `score_regime`) を利用するには OpenAI API キー（環境変数 `OPENAI_API_KEY` または関数引数）が必須です。未設定の場合は ValueError が発生します。
- Settings.env は "development", "paper_trading", "live" のみ許容します。不正な値を設定すると ValueError が発生します。
- .env の自動読み込みはプロジェクトルートの検出に依存します（.git か pyproject.toml）。配布後の利用やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを抑止してください。
- DuckDB に対する executemany の空リストバインドに起因する問題を回避するため、書き込み時は空チェックを行っています。データベースのバージョン差に注意してください。

### Implementation / Testing helpers
- OpenAI 呼び出しを内部関数 `_call_openai_api` に抽出しているため、unittest.mock.patch で差し替えてテスト可能です（`kabusys.ai.news_nlp._call_openai_api` と `kabusys.ai.regime_detector._call_openai_api` は独立実装）。

---

もしCHANGELOGに追記してほしい特定の変更点（例: リリース日を別にする、機能の優先度付け、既知の制約の詳細など）があればお知らせください。