# Changelog

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用しています。

注：
- 日付はリポジトリ内のコード内容から推測して付与しています。
- 記載はソースコード（src/kabusys 以下）から推測できる機能・設計方針・既知の制約に基づいています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
初回リリース。日本株向けのデータ基盤・リサーチ・AIスコアリング・運用支援ユーティリティ群を提供します。

### Added
- パッケージ構成（kabusys）
  - パッケージ初期化でバージョンを管理: __version__ = "0.1.0"
  - パブリックサブパッケージ: data, research, ai, execution, monitoring, strategy（__all__ に基づく）

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを実装。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env のパース機能を実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応）
  - OS 環境変数を保護する protected ロジック（.env.local は override=True で上書き可／ただし OS 環境変数は保護）
  - 必須環境変数チェック用ヘルパ _require
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル / 環境種別（development/paper_trading/live）等をプロパティ経由で取得
  - 入力検証: KABUSYS_ENV / LOG_LEVEL の限定値チェック、パス値は Path に展開

- AI ニュース解析（kabusys.ai.news_nlp）
  - ニュースの銘柄ごとセンチメント解析機能 score_news を提供
  - タイムウィンドウ定義（JST基準）および calc_news_window ユーティリティを実装
  - raw_news と news_symbols を用いて銘柄ごとに記事を集約（記事数・文字数の上限付き）
  - OpenAI（gpt-4o-mini）へバッチ送信（最大 _BATCH_SIZE=20 銘柄/回）し、JSON モードでレスポンスを取得・検証
  - レスポンスバリデーション機構（JSON 復元、results 配列、code/score チェック、数値チェック、±1.0 でクリップ）
  - エラー耐性: レート制限/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、致命的でない場合は個別チャンクをスキップして処理継続
  - DB への冪等書き込み（DELETE → INSERT、部分失敗時に他銘柄の既存データを保護）
  - テスト容易化: _call_openai_api をパッチで差し替え可能

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジームを判定
  - マクロニュース抽出（マクロキーワードリストによるタイトルフィルタ）と LLM スコアリングを実装
  - LLM 呼び出しは独立実装で、API エラー時には macro_sentiment を 0.0 としてフェイルセーフ継続
  - レジームスコアの閾値により "bull"/"neutral"/"bear" を判定
  - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時にROLLBACK）

- データ関連（kabusys.data）
  - ETL パイプライン用の ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl から再エクスポート）
  - ETL 実装方針: 差分更新、バックフィル、品質チェック（quality モジュール連携）を備えた設計
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）
    - DB にデータがない場合は曜日ベース（土日非取引日）でフォールバック
    - calendar_update_job により J-Quants からカレンダーを差分取得し保存（バックフィルと健全性チェックを実装）
    - 最大探索日数制限（_MAX_SEARCH_DAYS）を導入し無限ループ回避

- リサーチモジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）
    - ボラティリティ・流動性（20日 ATR、相対ATR、20日平均売買代金、出来高比率）
    - バリュー（PER、ROE を raw_financials と prices_daily から計算）
    - DuckDB を用いた SQL ベースの実装、データ不足時は None を返す
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証）
    - IC（Information Coefficient）計算（calc_ic、スピアマンのランク相関）
    - ランク変換ユーティリティ（rank、同順位は平均ランク）
    - 統計サマリー（factor_summary、count/mean/std/min/max/median を計算）
  - zscore 正規化ユーティリティを kabusys.data.stats から re-export

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 機密情報（OpenAI API キー、J-Quants トークン、kabu API パスワード等）は環境変数経由で取得する設計。設定忘れ時に明確な ValueError を出すことで安全性向上。

### Design / Implementation Notes（設計上の特記事項）
- ルックアヘッドバイアス防止のため、すべての「target_date」ベース処理で datetime.today() / date.today() を直接参照しない設計を採用（テスト可能性と再現性の確保）。
- DuckDB を主要なローカルデータベースとして想定（prices_daily, raw_news, ai_scores, market_regime, raw_financials, market_calendar 等のテーブルを参照/更新）。
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を使い厳格なパースを実施。ただし不完全レスポンスに対して復元処理も実装。
- API 呼び出しのリトライは指数バックオフ。5xx/ネットワーク/429 を区別して処理。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 的な処理）して再実行可能性を高める。
- テスト容易性を考慮し、外部 API 呼び出しポイント（_call_openai_api など）はモック可能な実装にしている。

### Known issues / Limitations（既知の制約）
- OpenAI API を必須で使用する機能（score_news, score_regime）は API キーが未設定だと ValueError を送出する。CI/テスト環境ではモックが必要。
- news_nlp の JSON パースは復元ロジックを備えるが、LLM の極端に壊れた出力はスキップされ得る（該当チャンクは空スコア）。
- ETL/カレンダー周りは J-Quants クライアントに依存。外部 API の変更があった場合は jquants_client 側の対応が必要。
- 現バージョンでは PBR・配当利回り等の一部バリューファクターは未実装。
- kabu（発注）関連モジュールの実態（execution / strategy / monitoring 内の実装）はこのスナップショットでは明示されていないため、実際の発注処理・監視の機能範囲は別途確認が必要。

### Requirements / Environment（導入前チェック）
- 必須環境変数（例）
  - OPENAI_API_KEY（score_news / score_regime 実行時に必要）
  - JQUANTS_REFRESH_TOKEN（データ取得に必要）
  - KABU_API_PASSWORD（kabu API 利用時）
- 推奨: DuckDB を利用できる環境（sqlite は監視 DB 用に想定）
- .env/.env.local によるローカル設定を想定。自動読み込みはプロジェクトルートを基準に行われる。

---

（以降のリリースでは Breaking changes / Added / Changed / Fixed / Security を区分して追記してください）