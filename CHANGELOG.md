# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買システムの基礎機能群を実装・公開しました。主な追加点は以下のとおりです。

### 追加 (Added)

- パッケージ基盤
  - kabusys パッケージの初期化（__version__ = 0.1.0）。
  - 公開モジュール群の定義（data, strategy, execution, monitoring を __all__ に含める。各サブパッケージは順次実装予定）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル / 環境変数からの設定読み込みを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .git または pyproject.toml を基準にプロジェクトルートを探索する実装（CWD に依存しない）。
  - .env のパースを堅牢に実装（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - 必須設定取得ユーティリティ `_require` と Settings クラスを提供。
    - 必須プロパティ例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境（KABUSYS_ENV）の妥当性検証（development / paper_trading / live）
    - ログレベル（LOG_LEVEL）の妥当性検証

- データ (kabusys.data)
  - calendar_management: マーケットカレンダー管理と営業日判定ロジックを提供。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - market_calendar がない場合の曜日ベースフォールバック、DB 登録がある場合は DB 値を優先する整合的な設計。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル・保存処理を実装（健全性チェック・例外ハンドリングあり）。
    - テーブル存在チェックや NULL 値検出時のログ出力等、堅牢性を考慮した実装。
  - pipeline: ETL パイプラインの基礎実装。
    - ETLResult データクラス: ETL 実行結果・品質問題・エラーの収集・to_dict メソッドを提供。
    - テーブルの最大日付取得や存在チェック等のユーティリティ関数を実装。
    - 差分更新・バックフィル・品質チェックの設計に基づいた実装方針を反映。
  - etl: ETLResult の公開再エクスポート。

- 研究（Research）ツール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を用いた PER / ROE を計算（target_date 以前の最新財務データを使用）。
    - 全関数は DuckDB 接続を受け取り SQL ベースで実行。データ不足時の None 処理等を考慮。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（コード単位で結合、3 レコード未満は None）。
    - rank: 同順位の平均ランク処理を含むランク化ユーティリティ。
    - factor_summary: count / mean / std / min / max / median の統計を実装。
  - data.stats の zscore_normalize を再エクスポート。

- AI（kabusys.ai）
  - news_nlp:
    - score_news: raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出・ai_scores テーブルへ保存。
    - ニュースウィンドウ: JST 基準で「前日 15:00 ～ 当日 08:30」を対象（内部は UTC naive datetime を使用）。
    - バッチ処理: 最大 20 銘柄 / 回、各銘柄は最新最大 10 記事・3000 文字でトリム。
    - API リトライ戦略（429、ネットワーク断、タイムアウト、5xx）を実装（指数バックオフ）。
    - レスポンスの厳密バリデーション（JSON モード対応、余分な前後テキストの復元、results フィールド検証、コード照合、数値検証、スコアクリップ）。
    - DB への書き込みは冪等（該当 date/code を DELETE → INSERT）で、部分失敗時に既存スコアを保護する実装。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ保存。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
    - マクロニュース取得は news_nlp.calc_news_window を利用してウィンドウを算出、マクロキーワードでフィルタしたタイトルを LLM に渡す。
    - OpenAI 呼び出しは独立実装、リトライとフェイルセーフ（API 失敗時は macro_sentiment = 0.0）により堅牢化。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に処理。

### 仕様上の注意・設計方針 (Notes)

- DuckDB をデータレイヤに採用しており、多くの処理は SQL ウィンドウ関数で実装されています。
- すべての「日付基準処理」は datetime.today() / date.today() を直接参照しない設計を採用（外部から target_date を渡すことでルックアヘッドバイアスを防止）。
- 外部 API 呼び出し（OpenAI, J-Quants 等）はフェイルセーフ設計（API 失敗時のフォールバックや部分失敗時の保護）を優先。
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（引数または環境変数 OPENAI_API_KEY）が必須。
- .env の自動読み込みはプロジェクトルートの検出に依存。配布環境では自動ロードを意図的に無効化するオプションあり。
- 一部機能は jquants_client など外部モジュール（J-Quants 連携用）の存在を前提としています（実行には該当モジュール・API 資格情報が必要）。

### 既知の制限 (Known issues / Limitations)

- strategy / execution / monitoring サブパッケージは __all__ に含まれているが、本リリースでの実装は限定的または未実装の可能性があります。取引実行ロジックやモニタリングは今後のリリースで拡充予定。
- OpenAI のレスポンス形式は LLM の挙動に依存するため、実運用ではレスポンス変動に対する監視が必要です。
- DuckDB のバージョン依存の振る舞い（executemany の空リスト扱い等）を考慮した実装になっていますが、異なる環境での互換性確認を推奨します。

### セキュリティ（注意事項）
- 環境変数に API キーやパスワードを平文で配置する設計のため、運用時は適切なシークレット管理（Vault 等）を検討してください。
- .env の読み込み挙動はプロジェクトルート検出に依存するため、パッケージ配布後の環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用することを推奨します。

---

今後のリリースでは以下を予定しています（例）:
- strategy / execution の注文ロジック実装とシミュレーション機能
- モニタリングとアラート機能の拡充（Slack 通知等）
- テストカバレッジ拡大と CI パイプラインの整備

もし特定の項目について詳細な CHANGELOG 記載や、追記してほしい差分（例: 実装した関数の引数仕様、戻り値の詳細、例外動作など）があれば教えてください。