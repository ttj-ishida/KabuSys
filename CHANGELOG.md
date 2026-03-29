# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
リリース日付はパッケージ内の __version__ と現在のコード状態に基づき記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース

### 追加 (Added)
- パッケージのエントリポイントを追加
  - kabusys.__init__ にてバージョン "0.1.0" と公開モジュール一覧を定義。

- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルおよび既存の OS 環境変数から設定を自動読み込みする機能を追加。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に自ファイル位置から探索するため、CWD に依存しない。
  - .env 行パーサーで以下に対応：
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値におけるインラインコメント処理（直前がスペース/タブの場合のみ）
  - .env ファイル読み込み時に既存 OS 環境変数を保護する protected 機能（.env → .env.local の上書きルールを含む）。
  - Settings クラスを提供し、J-Quants / kabuステーション API / Slack / DB パス / 環境種別 / ログレベル等のプロパティ経由での取得とバリデーションを実装。
    - 必須環境変数が不足している場合は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装（不正値は ValueError）。
    - duckdb/sqlite パスのデフォルトと Path 化。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から target_date に対応するニュースウィンドウを計算し、銘柄ごとにまとめて OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを生成。
    - ニュースウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - チャンクング（デフォルト 20 銘柄）でのバッチ処理、1銘柄あたりの記事上限（10件）と文字数上限（3000 文字）を実装し、トークン肥大化へ対策。
    - OpenAI への呼び出しは JSON Mode を利用し、レスポンスのバリデーション（results 配列、code/score のチェック、数値変換、スコアの ±1 クリップ）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ付きリトライを実装。その他エラーはスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分失敗時に既存データを保護するため、取得済みコードのみ DELETE → INSERT の冪等更新を実行。
    - テスト容易性のため _call_openai_api をモック差し替え可能にしている。
    - 公開 API: score_news(conn, target_date, api_key=None) をエクスポート（kabusys.ai.__init__ で score_news を公開）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベースで raw_news からタイトルを取得（最大 20 件、キーワードリストを持つ）。
    - OpenAI 呼び出しは JSON Mode、リトライ / バックオフ / フェイルセーフ（API 失敗時に macro_sentiment=0.0）を実装。
    - レジームスコア合成式および閾値（BULL/BEAR）を定義し、結果を market_regime テーブルへ BEGIN/DELETE/INSERT/COMMIT で冪等的に書き込む。
    - DB クエリはルックアヘッドバイアスを避けるように target_date 未満のデータのみを参照する設計。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Liquidity（平均売買代金・出来高比率）、Value（PER、ROE）の計算関数を実装。
    - DuckDB のウィンドウ関数を活用し、営業日に依存した計算・データ不足時の None 処理を実装。
    - 公開 API: calc_momentum, calc_volatility, calc_value。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応、入力検証あり。
    - IC 計算（calc_ic）: Spearman のランク相関をランク付け（同順位は平均ランク）で計算。
    - ランク変換 (rank) とファクター統計サマリー (factor_summary) を実装。
    - pandas など外部ライブラリに依存せず純標準ライブラリと DuckDB で実装。
  - research パッケージ __init__ で代表的関数群を公開。

- データ管理 (kabusys.data)
  - calendar_management:
    - market_calendar テーブルを参照する営業日判定・前後営業日の取得・期間内営業日の取得・SQ 日判定ロジックを提供。
    - DB にカレンダーがない場合は週末（土日）を非営業日とするフォールバックを採用。
    - next_trading_day / prev_trading_day は最大探索範囲を設定して無限ループを防止。
    - calendar_update_job: J-Quants から差分でカレンダーを取得し、バックフィル・健全性チェックを行った上で冪等的に保存する処理を実装。
  - pipeline / etl:
    - ETLResult データクラスを追加し、ETL 実行の取得件数・保存件数・品質問題・エラー一覧を格納可能に。
    - 差分更新、バックフィル、品質チェック（quality モジュール経由）を行う ETL パイプライン設計に対応するユーティリティを実装。
    - jquants_client を介した安全な保存とエラーハンドリング、DuckDB テーブル存在チェックなどを実装。
  - etl を public に再エクスポート（kabusys.data.etl）。

### 変更 (Changed)
- （初版リリースのため該当なし）

### 修正 (Fixed)
- （初版リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーや各種トークンは Settings で必須チェックを行い、未設定時は明示的な例外 (ValueError) を発生させることで誤設定による意図しないネットワーク呼び出しを防止。

### 注意事項 / 設計・運用上のポイント
- 時刻/日付の扱いについて:
  - AI モジュールと ETL はルックアヘッドバイアス防止のため、datetime.today() / date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - calendar_management / news_nlp では UTC naive datetime を DB 比較用に用いる等、タイムゾーンに起因する取り扱いに注意。
- OpenAI 呼び出し:
  - JSON Mode を利用して厳密な JSON レスポンスを期待するが、レスポンスの前後に余計なテキストが混ざるケースの復元ロジックや堅牢なバリデーションを実装。
  - テストのため _call_openai_api をモック化可能。
- DuckDB との相互作用:
  - executemany に空リストを渡せない DuckDB バージョン（0.10 系）を考慮したガードを実装（params が空でないことをチェック）。
  - DB 書き込みはトランザクションで行い、例外時には ROLLBACK を試行し失敗ログを残す。
- フェイルセーフ:
  - LLM/API 失敗時はスコアを 0.0 にフォールバックしたり、該当チャンクをスキップして他コードのデータを保護するなど、運用を優先した設計。

---
今後のリリースでは以下を検討してください（例）:
- 評価済みのユニットテストと統合テストの追加（特に OpenAI モック、DuckDB テストデータセット）。
- 設計ドキュメント（StrategyModel.md, DataPlatform.md）の公開とサンプル ETL 実行シナリオ。
- エラーメトリクス／監視（Sentry / Prometheus）統合。