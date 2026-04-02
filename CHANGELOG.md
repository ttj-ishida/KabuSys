# Changelog

すべての注目すべき変更はこのファイルに記録されています。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使っています。

最新変更ログを上から順に並べています。

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-02

初回公開リリース。以下の主要機能と実装方針を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。
  - __version__ = "0.1.0" を設定。
  - 公開モジュール: data, strategy, execution, monitoring（__all__ にてエクスポート）。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードの有効/無効を KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で制御可能。
  - .env.local は .env より優先して上書き（ただし OS 環境変数は保護）。
  - .git または pyproject.toml を基準にプロジェクトルートを探索することで CWD に依存しない読み込みを実現。
  - .env パース機能：
    - export フォーマット対応、シングル/ダブルクォート内のエスケープ対応、コメント処理（クォート外の # を考慮）等。
  - Settings クラスによりアプリ設定をプロパティとして提供：
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / ログレベル / 環境種別判定等を提供。
  - 必須項目未設定時は明示的なエラーを投げる（_require）。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news / news_symbols をソースに、OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信して銘柄別センチメント（ai_scores）を生成。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で処理）。
    - チャンク処理（最大 20 銘柄/回）、1 銘柄あたり記事数 / 文字数上限を導入。
    - エラーハンドリング: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ、その他はスキップして処理継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーションとスコア ±1.0 クリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT）を行い、部分失敗時に既存レコードを保護。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに保存。
    - prices_daily は target_date 未満のデータのみを参照してルックアヘッドバイアスを排除。
    - マクロニュース抽出はキーワードベース、ニュースが存在しない場合は LLM を呼ばず macro_sentiment=0.0 とする。
    - OpenAI 呼び出しは独立実装、リトライ・エラー処理あり。DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等実行。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - market_calendar テーブルを用いた営業日判定ユーティリティ群を実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値を優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants からカレンダーを差分取得して保存。バックフィル（直近 N 日）・健全性チェック（将来日付異常時スキップ）を実装。
  - pipeline / etl モジュール
    - ETLResult データクラスを実装して ETL 実行結果を集約（fetch/save 件数、品質問題、エラー一覧など）。
    - 差分更新、バックフィル、品質チェックの設計方針とユーティリティを実装。
    - ETLResult.to_dict() により品質問題を辞書化して監査ログなどに利用可能。
    - data.etl で ETLResult を再エクスポート（公開インターフェース）。

- 研究用モジュール（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20日）、平均売買代金 / 出来高比率、PER / ROE 等を DuckDB クエリで計算する関数を実装。
    - データ不足時の扱い（None 戻し）やログを設計。
  - feature_exploration モジュール
    - 将来リターン calc_forward_returns（柔軟な horizons 引数、入力検証）、IC（calc_ic）計算、ランク化ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等の外部依存を使わない純 Python 実装。

### 変更 (Changed)
- 設計方針の明示
  - 多くのモジュールで「datetime.today()/date.today() を参照しない」「ルックアヘッドバイアスを防ぐため target_date 未満データを使用」等を実装方針として記載。
  - OpenAI 呼び出しの扱いについてモジュール間の結合を避け、テスト容易性のため _call_openai_api を patch で差し替え可能にした点を明記。

### 修正 (Fixed)
- レスポンスパースや API エラー時の堅牢性強化
  - JSON パース失敗・余分テキスト混入に対する復元ロジック（外側の {} を抽出）を追加。
  - APIError の status_code の有無に柔軟に対応する処理を追加。
  - DuckDB の executemany に対する空リストバグへの回避（空のときは実行しない）を実装。

### 既知の制限 / 注意点 (Known issues / Notes)
- OpenAI API キーは環境変数 OPENAI_API_KEY もしくは関数引数で指定する必要がある。未指定時は ValueError を送出する関数がある（news_nlp.score_news, regime_detector.score_regime）。
- gpt-4o-mini を前提とした JSON Mode を使用しているため、モデルや API バージョン差異によるレスポンス変化に注意が必要。
- 一部機能は DuckDB のバインドやバージョン依存の挙動（リスト型バインド等）を回避する実装になっているが、環境によって挙動差が出る可能性がある。
- 現フェーズでは PBR / 配当利回り等一部バリューファクターは未実装。

### セキュリティ (Security)
- 環境変数の自動ロード時に OS 環境変数を保護するため、ロード処理は既存の環境変数を上書きしない（デフォルト）。.env.local で上書き可能だが OS 環境変数は protected として保護される。

---

今後の予定（非網羅）
- strategy / execution / monitoring の実装充実（注文実行、監視アラート等）。
- 追加ファクター、バックテスト用ユーティリティ、より詳細な品質チェック。
- ドキュメント（使用例・API 仕様）の整備。