CHANGELOG
=========
すべての顕著な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース日はリポジトリの現行状態（このコードベース）に基づき付与しています。

[Unreleased]
-------------

なし

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ全体
  - 初期リリース。パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数の読み込み機能を実装。
    - プロジェクトルートの自動検出ロジックを実装（.git または pyproject.toml を探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS の既存環境変数を保護する protected 機能（上書き防止）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理等。
  - Settings クラスを提供（settings インスタンス経由で取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等のプロパティ。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev ユーティリティプロパティ。

- データプラットフォーム (kabusys.data)
  - ETL インターフェース
    - ETLResult データクラスの実装（kabusys.data.pipeline）を公開（kabusys.data.etl で再エクスポート）。
    - ETL 実行結果のシリアライズ to_dict（品質問題の要約含む）。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーの扱い（market_calendar テーブル）と夜間バッチ更新 job を実装。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar 未取得時は曜日ベースでフォールバック（週末は休場）。
    - calendar_update_job: J-Quants からの差分取得、バックフィル、健全性チェック、冪等保存の実装。
    - 最大探索日数やバックフィル日数等の安全策を導入。

  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェックを想定したユーティリティ群を実装。
    - DuckDB でのデータ取得・最大日付取得のヘルパー、テーブル存在確認などを実装。
    - ETLResult に品質チェックの問題・エラー集約を保持。

- AI / ニュース NLP（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）に送信してセンチメントを取得。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄／コール）、1銘柄あたりのトリム設定（記事数／文字数）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト検証、スコアの数値検証、未知コード無視）。
    - 取得したスコアを ai_scores テーブルへ冪等的に置換（DELETE → INSERT、部分失敗時に他銘柄を保護）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。
  - レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の組合せで市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily から ma200_ratio を算出し、raw_news からマクロキーワードでフィルタした記事タイトルを抽出して LLM に投げる。
    - OpenAI API の堅牢なエラーハンドリング（リトライ、5xx 特別扱い、フェイルセーフで macro_sentiment=0.0）を実装。
    - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、ROLLBACK 時のログ）。
    - テスト用に _call_openai_api を差し替え可能。
    - 設計上、ルックアヘッドバイアスを避けるための DB クエリ条件や日付参照ルールを厳守。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時の None 扱い。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務情報を取得し PER / ROE を算出。
    - DuckDB の SQL ウィンドウ関数を活用した効率的な実装。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得（LEAD を使用）。
    - calc_ic: スピアマン（ランク相関）による IC 計算（ペアが 3 未満なら None）。
    - rank: 同順位は平均ランクを返す実装（丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - デザイン方針: pandas など外部依存に頼らず標準ライブラリと DuckDB SQL で実装。

Changed
- （初回リリースのため該当なし）

Fixed
- OpenAI API 呼び出し周りでの堅牢性を強化（429/タイムアウト/ネットワーク断/5xx のリトライ、非 5xx の場合は即座にフォールバックして例外を上げない設計）。
- DuckDB バインド互換性を考慮した executemany の空リストチェック（DuckDB 0.10 対応）。

Security
- .env 自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 自動ロード時に OS 環境変数を保護する設計（.env による上書きを防止）。

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策: モジュール群（AI 評価・ファクター計算・ETL 等）は date/datetime の現在時刻取得を直接参照せず、呼び出し元から target_date を受け取る設計。
- DuckDB 互換性: SQL や executemany の扱いは DuckDB の既知の制約を考慮。
- 冪等性重視: データベース書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT想定の保存関数利用）。
- テスト容易性: OpenAI 呼び出し箇所を差し替えられるようにしてユニットテストでのモックを想定。

Known issues
- 初期リリースのため、strategy / execution / monitoring の具象実装は public API に名前空間を準備しているものの、この差分には含まれていません（将来のリリースで追加予定）。

参考
- この CHANGELOG はソースコード内の docstring・関数名・定数・設計コメントから推測して作成しています。実際の仕様や実装詳細はソースコードを参照してください。

-----
[Unreleased]: https://example.com/compare/0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/0.1.0