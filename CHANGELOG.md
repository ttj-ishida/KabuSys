# CHANGELOG

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  

最新: 0.1.0（初回リリース）

## [Unreleased]
- なし

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ初期リリース: kabusys — 日本株自動売買/データ基盤/リサーチ支援ライブラリ
  - パッケージバージョンは src/kabusys/__init__.py にて `__version__ = "0.1.0"` を設定。

- 環境設定 / 設定管理
  - .env ファイルおよび環境変数から設定を読み込む設定モジュール (kabusys.config) を追加。
  - 自動 .env ロード:
    - プロジェクトルートの検出は .git または pyproject.toml を起点に行うため CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env の行パーサは以下に対応:
    - コメント行、export プレフィックス、クォート付き値（バックスラッシュでのエスケープ対応）、インラインコメントの扱い等。
  - Settings クラスで主要な設定項目をプロパティとして提供:
    - J-Quants / kabu ステーション / LINE API / DB パス (DuckDB/SQLite) / 監視設定（PID, kill flag, CPU/MEM/DISK閾値）/ 環境 (development / paper_trading / live) / ログレベル の取得・バリデーション。
    - 必須項目は未設定時に ValueError を発生させる (_require)。

- AI モジュール
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に銘柄単位でニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - 特徴:
      - ニュース収集ウィンドウ: JST ベースで「前日 15:00 ～ 当日 08:30」を採用（内部では UTC naive datetime を使用）。
      - バッチ処理: 最大 20 銘柄/呼び出し、1銘柄あたり最大 10 記事・3000 文字にトリム。
      - 再試行 (exponential backoff): 429/ネットワーク断/タイムアウト/5xx をリトライ対象とする。
      - レスポンス検証: JSON パース、"results" リスト検査、コードの正規化、スコアの数値化・有限性チェック、±1.0 でクリップ。
      - フェイルセーフ: API 失敗時は部分スキップして処理継続。DB 書き込みは取得できた銘柄に限定して DELETE → INSERT の冪等更新を行う。
      - テスト容易性: OpenAI 呼び出し箇所をパッチできる設計。
      - 返り値は書き込んだ銘柄数。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）200日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次でレジーム（bull/neutral/bear）を判定。
    - 特徴:
      - MA200 乖離は target_date 未満のデータのみで算出（ルックアヘッド回避）。
      - マクロニュースはニュースタイトルをキーワードでフィルタ（最大 20 件）し、OpenAI にて JSON 出力で macro_sentiment を取得。
      - API 障害時は macro_sentiment = 0.0 として継続（フェイルセーフ）。
      - 合成スコアはスケーリング・クリッピングし閾値でラベル化。market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
      - OpenAI 呼び出しもテストで差し替え可能な分離実装。

- リサーチ / ファクター計算モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離 (不足時 None) を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。データ不足は None を返す。
    - calc_value: raw_financials から最新財務を参照して PER / ROE を計算（EPS が 0/欠損は None）。
    - 実装方針: DuckDB 上の SQL + Python による実装、prices_daily/raw_financials のみ参照（外部発注等アクセス無し）。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）で将来リターンを計算。ホライズン検証（1〜252）あり。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関 (IC) を計算。有効レコードが 3 未満なら None。
    - rank: 同順位の平均ランクを返すユーティリティ（丸めで ties の検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- データ基盤モジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理: market_calendar テーブルを基に営業日判定 (is_trading_day)、翌営業日/前営業日取得 (next_trading_day/prev_trading_day)、期間内営業日列挙 (get_trading_days)、SQ 日判定 (is_sq_day) を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック（週末除外）で一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・健全性チェックを行い market_calendar を冪等に更新（jq.fetch_market_calendar / jq.save_market_calendar を使用）。
  - ETL / pipeline:
    - ETLResult データクラスで ETL 実行結果を構造的に保持（取得数・保存数・品質検査結果・エラー等）。
    - pipeline モジュールの ETLResult を再エクスポート (kabusys.data.etl)。
    - ETL 方針: 差分更新、バックフィル、品質チェックを行い、部分失敗でも他データを保護する保存ロジック（個別 DELETE → INSERT）を採用。

- モジュール再エクスポート / API
  - kabusys.research の __all__ に主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - kabusys.ai.__init__ は score_news を公開（regime_detector はモジュールとして存在、直接インポート可能）。
  - kabusys.data.etl は ETLResult を公開。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーの取得方法:
  - 関数に api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定する設計。未設定時は ValueError を送出して明示的に失敗させる（誤った秘密管理を防止）。
- 環境変数の上書き制御:
  - 自動 .env ロード時に既存の OS 環境変数を保護する仕組み（protected set）を導入。

### 既知の制約 / 注意点 (Notes)
- DuckDB を主要な永続化・計算基盤として想定。SQL 文は DuckDB のウィンドウ関数等を前提に記述。
- 日付処理はルックアヘッドバイアス回避のため target_date を引数で与える方式を採用し、内部で date.today() / datetime.today() に依存しない設計方針を守る。
- OpenAI 呼び出し箇所はテスト時にパッチできるように関数分離されている（ユニットテスト対応）。
- 一部モジュール（例: kabusys.ai.regime_detector）は ai.__init__.py で自動公開されていないため、必要に応じて明示的にインポートして利用すること。

---

変更履歴に関する要望・誤りの指摘や、将来的なセクション（Breaking changes 等）の追加の要望があればお知らせください。