# CHANGELOG

すべての変更は Keep a Changelog の慣習に従い、セマンティックバージョニングに基づいて記載しています。

※この CHANGELOG は提供されたコードベースから実装内容を推測して作成しています。リリース日には本ファイル作成日（2026-04-01）を使用しています。

## [0.1.0] - 2026-04-01

初回公開リリース。日本株自動売買・データ基盤・リサーチ向けのコア機能群を実装。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - package-level エクスポート: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して判定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
  - .env パーサを実装（export 形式対応、シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメント処理をサポート）。
  - Settings クラスを提供し、主要設定値をプロパティで取得可能:
    - J-Quants / kabuステーション / Slack / データベース（duckdb, sqlite）/監視（PID, CPU/MEM/DISK閾値）/システム（環境, ログレベル）など。
  - 必須項目未設定時は ValueError を送出する _require() を実装。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いたセンチメント解析を行って ai_scores テーブルへ書き込み。
    - 処理の特徴:
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算（ルックアヘッド防止）。
      - 1 銘柄あたりの記事数・文字数上限（トリミング）を実装。
      - バッチ処理（最大 20 銘柄/コール）と冪等的 DB 書き込み（DELETE → INSERT）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ。
      - レスポンス検証（JSON 抽出・results フォーマット検証・スコア数値性チェック・±1.0 クリップ）。
      - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch によりモック可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して、日次で市場レジーム（"bull" / "neutral" / "bear"）を判定し market_regime テーブルへ冪等書き込み。
    - 処理の特徴:
      - MA 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
      - マクロニュースは raw_news からキーワードでフィルタ（最大記事数制限）。
      - OpenAI 呼び出しは独立実装で、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
      - API エラーに対するリトライとロギング、DB トランザクション（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。

- データ基盤（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - 提供関数:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - calendar_update_job: J-Quants からの差分取得 → 保存（バックフィル・健全性チェック込）
    - DB 登録値優先、未登録日は曜日ベースのフォールバック（土日除外）で一貫した判定を実現。
    - 最大探索日数・バックフィル・先読み等の安全対策を実装。
  - pipeline / ETL
    - ETLResult データクラスを追加（ETL 実行結果の集約: fetched/saved 件数、品質問題、エラー一覧等）。
    - ETL パイプライン設計に関する内部ユーティリティを実装（テーブル存在確認、最大日付取得等の補助関数を含む）。
    - 設計方針として差分更新・バックフィル・品質チェックの収集（Fail-Fast ではなく呼び出し元で判定）を採用。
  - etl モジュールは pipeline.ETLResult を再エクスポート（公開インターフェース）。

- リサーチ（kabusys.research）
  - factor_research
    - Momentum / Volatility / Value の計算関数を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時は None）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（部分窓での算出対応）
      - calc_value: per, roe（raw_financials から最新財務データを取得して計算）
    - DuckDB を用いた SQL ベースの実装。結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration
    - 将来リターン・IC・統計サマリを提供:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic: スピアマンのランク相関（情報係数）を実装（有効レコードが 3 未満の場合は None）。
      - rank: 同順位は平均ランクを採用するランク変換ユーティリティ（丸めで ties の検出漏れを防止）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

- 複数モジュールに共通する設計上の配慮
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計（target_date を引数として受ける）。
  - DuckDB を主要なデータストアとして利用し、トランザクション／冪等書き込み（DELETE → INSERT / ON CONFLICT）を採用。
  - OpenAI（gpt-4o-mini）を利用する箇所は、リトライ・バックオフ・レスポンス検証およびフェイルセーフの設計を実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

### Known issues / Notes（既知の制限・注意点）
- pipeline._get_max_date の実装が提供コード内で途中となっているように見えます（末尾で不完全に終わっている）。ETL 動作時に該当関数が呼ばれる場合、実行時エラーや未定義動作を引き起こす可能性があります。リリース前に実装の完了・テストを推奨します。
- OpenAI の API 呼び出しは外部ネットワーク依存であるため、実行環境に API キー（OPENAI_API_KEY）と適切なネットワークアクセスが必要です。API 利用に関連するコストと利用制限に注意してください。
- .env パーサは多くのケースに対応していますが、極端な形式の .env や特殊文字に対しては想定外の挙動をする可能性があります。重要な機密情報の取り扱いは OS 環境変数での管理を推奨します。
- DuckDB バージョン依存の挙動（executemany に空リストを渡せない等）を考慮した実装がされていますが、利用する DuckDB のバージョンでの動作確認を行ってください。

---

今後の予定（想定）
- pipeline の未完了箇所修正と ETL 実行のエンドツーエンドテスト。
- strategy / execution / monitoring モジュールの詳細実装・ドキュメント追加。
- CI / テストケース整備（特に OpenAI API 呼び出しのモックを用いた単体テスト）。