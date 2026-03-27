# Changelog

すべての変更は Keep a Changelog 準拠で記載します。  
現在のバージョンはパッケージ内の __version__ に合わせて 0.1.0 としています。

## [Unreleased]

- 開発中の変更無し。

## [0.1.0] - 2026-03-27

初回リリース — KabuSys: 日本株自動売買 / 研究 / データ基盤のユーティリティ群を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初版を公開。__version__ = "0.1.0"。
  - パッケージの公開 API: data, strategy, execution, monitoring（__all__）。

- 設定管理 (kabusys.config)
  - .env / .env.local / OS 環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）により CWD に依存しない自動ロードを実現。
  - .env パーサは export 形式、クォート・エスケープ、インラインコメント等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化、環境変数保護（protected keys）対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル 等のプロパティを公開（必須キー未設定時はエラーを投げる）。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - ニュース記事群を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（JSTベースの前日15:00〜当日08:30相当）を実装。
    - バッチ（最大20銘柄）での送信、1銘柄あたりの記事件数・文字数上限、JSON Mode を使ったレスポンスパース、レスポンスバリデーション、スコアクリップ（±1.0）、DuckDB への冪等書き込み（DELETE→INSERT）などを実装。
    - レート制限/ネットワーク/サーバーエラーに対する指数バックオフリトライとフェイルセーフ（失敗時は該当チャンクをスキップ）を実装。

  - regime_detector.score_regime
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - prices_daily と raw_news を利用するデータフローを実装。API 呼び出し失敗時は macro_sentiment を 0.0 として継続するフェイルセーフを採用。
    - OpenAI 呼び出しは専用の内部実装として切り離し、テスト時の差し替え (patch) を容易にしている。

- データ基盤 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理用ユーティリティを実装。market_calendar テーブルを用いた判定（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を提供。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバックを行う設計。
    - calendar_update_job により J-Quants から差分取得・バックフィル・保存を行うバッチ処理を実装。健全性チェック（未来日付の異常検知）を含む。
  - pipeline / ETL
    - ETLResult dataclass を導入し、ETL 実行結果（取得数/保存数/品質検査問題/エラー）を構造化して返す。
    - 差分更新・バックフィル・品質チェックを想定したユーティリティ群を実装。テーブル最大日付取得等を提供。
  - etl モジュールで ETLResult を再エクスポート。

- 研究用ユーティリティ (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日ATR）、流動性指標（20日平均売買代金・出来高比）やバリュー（PER, ROE）計算機能を実装。
    - DuckDB 上で SQL + Python により計算し、ファクター結果を date/code キーの辞書リストで返す設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、Information Coefficient（calc_ic）、rank、factor_summary（統計サマリー）を実装。
    - pandas 等に依存せず標準ライブラリでの実装。
  - research パッケージの __init__ で主要関数を公開。

### 変更点 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- ルックアヘッドバイアス対策を徹底
  - 各種関数（score_news, score_regime, factor 計算等）は datetime.today()/date.today() を内部参照しない設計。全て target_date 引数ベースで動作。
  - prices_daily クエリは target_date 未満・未満/範囲指定等で未来データ参照を防止。

- レジリエンス・堅牢化
  - OpenAI 呼び出し周りにリトライ（429/ネットワーク/タイムアウト/5xx）、バックオフ、最終フォールバックロジックを導入。
  - JSON モードの応答に対して前後に余計なテキストが混入するケースを考慮して復元ロジックを実装。
  - DuckDB の executemany に対する空リスト制約（バージョン互換性）を考慮した安全な書き込み処理を実装（空の場合は実行をスキップ）。
  - DB 書き込み時は冪等操作（DELETE → INSERT / BEGIN/COMMIT/ROLLBACK）で部分失敗からの保護を実装。

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY で決定される。キーはパッケージ内にハードコードしない方針。
- .env 読み込みはプロジェクトルート検出と protected keys により既存 OS 環境変数の上書きを保護。

### 開発者向けメモ
- テスト容易性のため、OpenAI 呼び出し内部関数（news_nlp._call_openai_api, regime_detector._call_openai_api など）を patch して動作を差し替えられる設計になっています。
- DuckDB コネクションを引数として受け取り純粋に SQL / DB 上のデータだけで計算する設計のため、本番の発注 API 等には直接アクセスしません（安全性・テスト性の向上）。
- 公開 API（主要関数）
  - kabusys.config.settings
  - kabusys.ai.score_news, kabusys.ai.score_regime
  - kabusys.data.calendar_management.*（is_trading_day 等）
  - kabusys.data.pipeline.ETLResult
  - kabusys.research.*（calc_momentum 等）

---

追記・補足が必要であれば、特定モジュールごとにより詳細な変更点や注意点（入力スキーマ・DB テーブル定義の前提等）を書き起こします。