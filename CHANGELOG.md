# CHANGELOG

すべての注目に値する変更をこのファイルに記載します。  
このプロジェクトは Keep a Changelog のフォーマットに従っており、セマンティックバージョニングを採用します。

なお、この CHANGELOG はコードベース（src/kabusys 以下）から推測して作成しています。実装の意図や詳細は該当ソースを参照してください。

## [0.1.0] - 2026-03-31

### Added
- パッケージ基盤
  - kabusys パッケージ初期リリース。__version__ = "0.1.0"。
  - パッケージ公開 API（__all__）として data, strategy, execution, monitoring を露出。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local ファイルおよび OS 環境変数から設定値を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に決定（CWD非依存）。
    - 読み込み優先度: OS 環境 > .env.local > .env
    - .env 読み込みの上書き制御（override）と OS 環境変数保護（protected）をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env の各行のパースは export 句、クォート、エスケープ、インラインコメントに対応。
  - Settings クラスでアプリケーション設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - DB パスや監視閾値、ランタイム環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）の検証を実装。
  - 必須値未設定時は ValueError を送出するヘルパー _require を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
    - 対象ニュースウィンドウは JST 基準で「前日 15:00 〜 当日 08:30」（内部は UTC naive に変換して比較）。
    - チャンク処理（最大 20 銘柄／API 呼び出し）、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - API の 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンス検証: JSON パース、"results" リスト、各要素の code と score の妥当性チェック（未知コードの無視、スコアは ±1.0 にクリップ）。
    - 書き込みは部分失敗に配慮し、対象コードのみを DELETE → INSERT で置換（冪等性確保、DuckDB executemany の空リスト注意対応）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - テスト用に _call_openai_api を patch して差し替え可能（テストフック）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%、スケール 10）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - マクロニュースは raw_news からマクロキーワードでフィルタ。最大 20 記事を LLM に送信して JSON で macro_sentiment を取得。
    - LLM 呼び出しは gpt-4o-mini を使用、リトライ・バックオフ・5xx ハンドリングを実装。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジームスコアを計算し、market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込み。
    - API キーの解決と未設定時のエラー処理（ValueError）を実装。
    - テスト用に _call_openai_api を patch して差し替え可能（疎結合設計）。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを基に営業日判定、次/前営業日の計算、期間内営業日一覧取得、SQ日判定などのユーティリティを提供。
    - DB 未取得時は土日ベースのフォールバックを採用（整合性を保つため next/prev/get のロジックで一貫した挙動）。
    - 最大探索日数制限（_MAX_SEARCH_DAYS = 60）や先読み・バックフィル設定、健全性チェック（将来日付の異常検出）を実装。
    - calendar_update_job により J-Quants から差分取得し冪等保存（fetch / save の呼び出しラッパー）。API 例外や保存失敗時は安全に 0 を返す。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスで ETL 実行結果を構造化（取得数・保存数・品質問題・エラー一覧・ユーティリティメソッド to_dict）。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。J-Quants クライアント（jquants_client）との統合ポイントを定義。
    - 内部ユーティリティでテーブル存在チェック、最大日付取得などを実装（DuckDB を前提）。
    - etl モジュールで ETLResult を再エクスポート。

- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。部分ウィンドウでの算出・NULL取扱いを考慮。
    - calc_value: raw_financials の最新財務データ（target_date 以前）と株価を組み合わせて PER（EPS が 0/欠損なら None）と ROE を計算。
    - DuckDB の SQL ウィンドウ関数を利用し、prices_daily / raw_financials のみを参照する安全設計（発注 API 等にアクセスしない）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）における将来リターンを一度の SQL で取得。horizons のバリデーションあり（1〜252）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。レコード数不足や分散ゼロを考慮して None を返す場合あり。
    - rank: 同順位は平均ランクを返すランク変換ユーティリティ（浮動小数の丸めによる tie 対策あり）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算する統計サマリ機能（None値は除外）。
    - すべての機能は外部依存（pandas 等）なしで標準ライブラリ + DuckDB のみで実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 動作上の重要点
- OpenAI と連携する機能（news_nlp, regime_detector）はいずれも OPENAI_API_KEY を引数で注入可能。テスト容易性のため外部呼び出し部分を patch できる設計になっている。
- LLM レスポンスは JSON モードで期待するが、JSON 以外のノイズを含む場合に備えた復元ロジックや堅牢なバリデーションを実装しており、パース失敗や API エラー時は安全側のデフォルト（0.0 やスキップ）で処理継続する。
- DB 書き込みは冪等性を意識しており、既存行の置換（DELETE → INSERT）やトランザクション（BEGIN/COMMIT/ROLLBACK）を使用している。ROLLBACK が失敗した場合にログ出力するガードあり。
- カレンダー・ETL 周りは J-Quants クライアント（jquants_client）との統合を想定。calendar_update_job や ETLResult などは運用バッチでの利用を想定している。
- DuckDB のバージョン差異（executemany の空リスト取り扱い等）に配慮した実装が多数含まれる。

今後のリリースでは以下を想定:
- strategy / execution / monitoring の具象実装（現在は名前空間のみ）。
- 追加の品質チェックルール、ジョブスケジューリング、運用監視（Slack 通知等）の実装拡張。

---

参考: 各モジュール・関数の実装はソースコード（src/kabusys/...）を参照してください。