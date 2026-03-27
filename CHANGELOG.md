# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

※日付はコード解析時点のリリース想定日です。

## [Unreleased]

## [0.1.0] - 2026-03-27
初期リリース。日本株の自動売買／データ基盤／リサーチ向けのコア機能を実装しました。主に以下のモジュールを提供します。

### Added
- パッケージ基盤
  - パッケージ名 `kabusys` を導入。バージョンを `0.1.0` として公開。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理 (`kabusys.config`)
  - .env/.env.local の自動ロード機能を実装（OS 環境変数優先、.env.local は上書き）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用等）。
  - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント扱いの注意）。
  - 環境変数保護（既存 OS 環境変数を protected として扱う）および override オプション実装。
  - Settings クラスを提供し、以下の設定プロパティを取得可能:
    - J-Quants / kabuステーション / Slack トークン類（必須チェック付き）
    - DB パス（duckdb/sqlite）を Path 型で取得
    - 実行環境（development / paper_trading / live）とログレベルのバリデーション
    - is_live / is_paper / is_dev の便宜プロパティ

- AI（自然言語処理）機能 (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp`)
    - target_date に基づくニュース収集ウィンドウ計算（JST→UTC 変換）。
    - raw_news + news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントを算出。
    - バッチサイズ、最大記事数/文字数制限、JSON Mode の利用、レスポンス検証・スコアクリップ（±1.0）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
    - スコアは ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT の置換処理、部分失敗時の保護）。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能に実装。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news を参照し、market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しは独立実装、API エラーやパース失敗時は macro_sentiment = 0.0 のフォールバック（フェイルセーフ）。
    - リトライロジック（最大リトライ回数、指数バックオフ）と 5xx の判別対処を実装。

- データプラットフォーム関連 (`kabusys.data`)
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - market_calendar テーブルに基づく営業日判定 API を提供（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB データがない場合は曜日ベース（土日非営業）でフォールバック。
    - JPX カレンダーを J-Quants API から差分取得する夜間バッチ（calendar_update_job）を実装。バックフィルや健全性チェック（将来日付の異常検出）を備える。
  - ETL / パイプライン基盤 (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL 実行結果を表す ETLResult dataclass を実装（取得数・保存数・品質問題・エラーの集約）。
    - 差分取得、バックフィル、品質チェック設計に沿ったヘルパー関数（テーブル存在確認・最大日付取得など）。
    - `kabusys.data.etl` で ETLResult を再エクスポート。

- リサーチ（ファクター・特徴量探索） (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS=0/欠損時は None）。
    - DuckDB SQL を中心に実装し、外部 API には依存しない設計。
  - 特徴量探索・統計 (`kabusys.research.feature_exploration`)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク相関）による IC 計算（最低サンプル数チェック）。
    - rank: 同順位は平均ランクで処理（丸めで tie 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージ __init__ で主要関数を公開。

### Security
- OpenAI API キーは引数で注入可能な設計（api_key 引数優先、未指定時は環境変数 OPENAI_API_KEY を参照）。未設定時は明示的に ValueError を送出して安全性を担保。

### Design / Behavior notes
- ルックアヘッドバイアス防止:
  - 各種処理（ニュースウィンドウ、ファクター計算、レジーム判定等）は datetime.today() / date.today() を直接参照せず、target_date 引数に基づいて処理する実装方針。
- 冪等性:
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 想定）して部分失敗時のデータ保護に配慮。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants）呼び出し失敗時は局所的にフォールバックまたはスキップして処理継続する設計（例: macro_sentiment=0.0、スコア取得失敗は空辞書）。
- テスト容易性:
  - OpenAI 呼び出しのラッパー関数はテストで差し替え可能（unittest.mock.patch を想定）。

### Fixed
- 初期リリースのため該当なし。

### Changed
- 初期リリースのため該当なし。

### Deprecated
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Known limitations / TODO
- strategy / execution / monitoring の詳細実装はこのリリースでは明示されていない（パッケージ公開名として存在）。
- PBR や配当利回り等の一部バリューファクターは未実装（calc_value の注記参照）。
- DuckDB バインドの一部（executemany の空リスト制約など）に対する互換性考慮は実装済みだが、運用時の DB バージョン差異に注意が必要。

---

過去リリース履歴が存在する場合はここに古いバージョンを追加します。