# Keep a Changelog
すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]
（今後の変更点をここに記載）

---

## [0.1.0] - 2026-04-03
初回公開リリース — 基本データプラットフォーム / 研究用ユーティリティ / AI スコアリング / カレンダー管理を含む日本株自動売買フレームワークを提供します。

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - 主要サブパッケージ公開: data, research, ai, execution（参照用）、strategy（参照用）、monitoring（参照用）

- 環境設定
  - 環境変数読み込みユーティリティを提供する `kabusys.config` を追加
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
    - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応
    - Settings クラスを提供し、アプリ設定（J-Quants トークン、kabu API、LINE トークン、DB パス、監視閾値、実行環境判定 etc.）をプロパティ経由で取得
    - 必須値取得時の明示的エラー（_require）を実装

- データ取得・ETL 基盤
  - `kabusys.data.pipeline` に ETLResult クラスを追加（ETL 実行結果の構造化、品質問題・エラーの集約）
  - ETL 設計に関するユーティリティ、差分更新・バックフィル方針をコードに反映（定数: _MIN_DATA_DATE, backfill 等）
  - `kabusys.data.etl` で pipeline の型を再エクスポート

- マーケットカレンダー管理
  - `kabusys.data.calendar_management` を実装
    - market_calendar テーブルを基に営業日判定/is_sq_day/next/prev/get_trading_days を提供
    - DB にデータが無い場合は曜日ベースでフォールバック（週末を非営業日と扱う）
    - calendar_update_job: J-Quants から差分フェッチして冪等的に保存（バックフィル・健全性チェックを実装）
    - 最大探索日数やバックフィル日数等の安全策を導入（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）

- AI ニュース NLP（銘柄別センチメント）
  - `kabusys.ai.news_nlp` を実装
    - raw_news + news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事抽出を実装（calc_news_window）
    - バッチ単位で最大銘柄数や文字数を制限してトリム（_BATCH_SIZE, _MAX_CHARS_PER_STOCK 等）
    - JSON mode（response_format={"type":"json_object"}）を使用、レスポンスの堅牢なバリデーションとクリッピング（±1.0）
    - リトライ戦略（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフを実装
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に設計（_call_openai_api で patch 可能）
    - DB 書き込みは部分成功を考慮し、対象コードのみ DELETE → INSERT で置換（DuckDB の executemany 空リスト回避を考慮）

- AI 市場レジーム判定
  - `kabusys.ai.regime_detector` を実装
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）
    - ma200_ratio の計算は target_date 未満のデータのみを利用してルックアヘッドを防止
    - マクロ記事抽出（マクロキーワードリスト）→ OpenAI 呼び出し（gpt-4o-mini）→ JSON パース→ 合成スコア
    - API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）
    - DB への書き込みは冪等性を保つ（BEGIN/DELETE/INSERT/COMMIT、例外時は ROLLBACK）

- 研究（Research）ユーティリティ
  - `kabusys.research` パッケージを追加し、主要関数をエクスポート
    - factor_research: calc_momentum, calc_value, calc_volatility を実装
      - Momentum: 1M/3M/6M リターン、200日 MA 乖離（未満行数は None）
      - Volatility: 20日 ATR、ATR の相対値、20日平均売買代金、出来高比率
      - Value: raw_financials から最新財務を取得して PER、ROE を計算
    - feature_exploration: calc_forward_returns（複数ホライズン）、calc_ic（Spearman ランク相関）、factor_summary（統計量）、rank（同順位は平均ランク）を実装
    - zscore_normalize を data.stats から再エクスポートする仕組み

- DuckDB を前提とした SQL + Python ハイブリッド設計
  - 多くの分析/ETL 関数は DuckDB 接続（DuckDBPyConnection）を受け取り SQL ウィンドウ関数で効率的に処理
  - 日付はすべて date もしくは UTC naive datetime で扱い timezone 混入を回避
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照する実装を避け、必ず target_date を外部から注入

### 変更 (Changed)
- （なし / 初版のため該当なし）

### 修正 (Fixed)
- （なし / 初版のため該当なし）

### セキュリティ (Security)
- API キー等の必須情報は Settings 経由で取得し、未設定時は明示的に ValueError を発生させることで安全側に設計

### 運用ノート (Notes for operators)
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（kabu API の場合）、OPENAI_API_KEY（AI 機能利用時）
- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env → .env.local の順で読み込み
  - OS 環境変数が優先され、.env.local は上書きを行う（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
- DB
  - デフォルトで DuckDB を想定（設定は Settings.duckdb_path / sqlite_path）
- OpenAI 呼び出し
  - gpt-4o-mini を想定。レスポンスは JSON モードで受け取り、パースやバリデーションの失敗はログを出してフェイルセーフでスキップ/中立値を返す
  - テストでは _call_openai_api の差し替えを想定

---

今後のバージョンでは以下の点の拡張が想定されます（ロードマップ例）:
- 実行（execution）・監視（monitoring）周りの具体的なプロセス管理、PID / kill フラグ操作の追加
- Strategy 実行エンジン（発注・ポートフォリオ管理）と paper/live 切替の完成
- 品質チェック（kabusys.data.quality）と ETL の自動スケジューリング
- テストカバレッジ拡充と CI パイプラインの整備

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース履歴や日付はリポジトリ運用ポリシーに従って更新してください。）