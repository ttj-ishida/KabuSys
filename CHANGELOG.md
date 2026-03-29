Changelog
=========
すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

Unreleased
----------
（なし）

0.1.0 - 2026-03-29
-----------------
初期リリース

Added
- パッケージ基本
  - パッケージエントリポイントを追加。バージョン: `kabusys.__version__ == "0.1.0"`。
  - パッケージ公開要素: data, strategy, execution, monitoring（`__all__`）。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - プロジェクトルートの検出は __file__ を起点に `.git` または `pyproject.toml` を探索するため、CWD に依存しない実装。
  - .env パーサ: `export KEY=val` 形式の対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理（クォート外の `#` はスペース前後ルールでコメント扱い）をサポート。
  - 環境変数必須チェック用ヘルパ `_require` とアプリ設定ラッパ `Settings` を提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベルなど）。`KABUSYS_ENV` と `LOG_LEVEL` の値検証を行うプロパティを実装。
  - デフォルト DB パス: DuckDB -> `data/kabusys.duckdb`、SQLite -> `data/monitoring.db`。

- AI 関連（src/kabusys/ai/*.py）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信し、銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を `calc_news_window` で提供。DB 比較用に UTC naive datetime を返す。
    - 1チャンクあたり最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字でトリムするトークン肥大化対策。
    - API 呼び出しでの 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフリトライ実装。失敗時は該当チャンクをスキップし、例外を上位へ伝播しない（フェイルセーフ）。
    - レスポンス検証: JSON パース、"results" リスト、各要素の code/score 検証、未知コードの無視、数値検証、±1.0 でクリップ。
    - DuckDB の executemany に関する互換性（空リスト禁止）を考慮して部分削除→挿入で冪等保存。
    - テスト容易性のため、OpenAI 呼び出し箇所は `_call_openai_api` を通す（unittest.mock.patch により差し替え可能）。
    - 公開関数: `score_news(conn, target_date, api_key=None)`。OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` を参照。キー未設定時は ValueError を送出。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を組み合わせて日次レジーム（'bull' / 'neutral' / 'bear'）を判定し `market_regime` テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出はマクロキーワード集合（日本・米国など）でフィルタしてタイトルを取得。最大 20 記事を LLM へ投入。
    - LLM 呼び出しは gpt-4o-mini の JSON mode を使用、レスポンスは {"macro_sentiment": float} 形式を期待。API エラー時は macro_sentiment=0.0 にフォールバックして継続。
    - MA 乖離の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。データ不足時は中立（1.0）扱い。
    - 公開関数: `score_regime(conn, target_date, api_key=None)`。API キー未設定時は ValueError。

- リサーチ（src/kabusys/research/*.py）
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。
    - Volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から最新を取得）。
    - DuckDB を利用した SQL / ウィンドウ関数ベースの実装。データ不足時の None 処理やログ出力を考慮。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）: `calc_forward_returns`。ホライズン上限と入力検証あり。
    - IC（Spearman の ρ）計算: `calc_ic`（ランク相関）。有効レコードが 3 未満の場合は None。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、丸めで ties の誤差対策）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）。

- データプラットフォーム（src/kabusys/data/*.py）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を実装。DB の market_calendar を優先、未登録日は曜日ベースのフォールバック（weekend のみ非営業）を行う。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）による無限ループ防止。DB の不整合（NULL）に対する警告とフォールバック。
    - 夜間バッチ job: `calendar_update_job(conn, lookahead_days=90)`。J-Quants クライアント (`jquants_client`) を使い差分取得・保存。バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（未来日付の異常）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETL 結果型 `ETLResult` を提供（取得数・保存数・品質問題・エラー記録など）。
    - 差分更新のためのヘルパ `_get_max_date`、テーブル存在確認 `_table_exists` 等を提供。
    - 設計上、品質チェックモジュール（quality）と連携し、重大な品質問題が検出されても ETL 自体は継続して検出結果を返す（Fail-Fast しない）。
    - デフォルトバックフィル日数、カレンダー先読み日数等を定義。

- テスト/運用性
  - OpenAI 呼び出しを抽象化した内部関数を用意し、テスト時に差し替え可能（unittest.mock.patch により差し替え）。
  - 多くの処理で例外発生時にフェイルセーフ（ゼロや空辞書で続行）することでバッチ運用に適した堅牢性を重視。
  - DuckDB の互換性問題（executemany に空リストを渡せない）を考慮した実装。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- 環境変数に敏感な値（API キー等）は Settings を通じて取得し、明示的に必須チェックを行うことで設定漏れを早期に検出。
- .env の自動ロードはプロセス起動時に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テストや CI の誤作用を防止。

Notes / 注意事項
- 外部依存・実行前提
  - DuckDB を利用するため、実行環境に DuckDB が必要です。
  - OpenAI クライアント（openai ライブラリ）を用いるため、API キーとネットワークアクセスが必要です。
  - J-Quants 関連の ETL / calendar_update_job は jquants_client モジュールに依存（実行環境での API アクセス設定が必要）。
- ルックアヘッドバイアス対策
  - AI モジュールやリサーチ関数は内部で datetime.today()/date.today() を直接参照しないよう設計されています。すべての関数は caller が与える target_date を基準に計算します。
- DuckDB バインドに関する互換性
  - DuckDB（特に 0.10 系）では executemany に空リストを渡すと失敗するため、実装中で明示的に空チェックを行っています。
- ロギング
  - 各モジュールは適切な警告・情報ログを出力するように設計されています。デバッグや運用時に役立ちます。

今後の予定（例）
- strategy / execution / monitoring の詳細実装と統合テスト
- ai モジュールの評価・チューニング（プロンプト改善、モデル切替の検討）
- ETL の品質チェックルール追加と監査ログ強化

もし特定ファイルや機能についてさらに詳しい変更点（実装の意図、制約、使用例）をCHANGELOGの追記として反映したい場合は、対象を指定して教えてください。