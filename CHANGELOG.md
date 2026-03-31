# Changelog

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
標準的な慣例に従い、重大な変更・追加・修正点をカテゴリ別にまとめています。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-31
初回リリース。プロジェクトのコア機能（データ取得・ETL・カレンダー管理・リサーチ用ファクター計算・AI を用いたニュース分析・市場レジーム判定・設定管理）を実装しました。

### 追加（Added）
- パッケージ基礎
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。
  - パッケージ公開 API: __all__ に data, strategy, execution, monitoring を含める（将来的な拡張用の名前空間を準備）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - OS 側の環境変数を保護するため protected セットを使用し、.env の上書きを制御。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサを実装し、以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォートあり/なしでの差異）
  - Settings クラスを導入（ワーカーから直接使用可能）
    - J-Quants / kabu API / Slack / DB パス等のプロパティを提供（必須項目は未設定時に ValueError を送出）。
    - env, log_level の検証（許容値チェック）と便宜メソッド is_live / is_paper / is_dev。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など。

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols に基づき銘柄ごとにセンチメントを算出して ai_scores に書き込む。
    - ニュース収集ウィンドウ: target_date の「前日 15:00 JST 〜 当日 08:30 JST」を UTC に変換して利用（ルックアヘッドバイアス防止）。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチ処理（最大 20 銘柄 / バッチ）。
    - 1 銘柄あたり記事数と文字数の上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を導入してトークン肥大化を抑制。
    - リトライ・バックオフ: 429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフで再試行。
    - レスポンス検証: JSON 抽出、"results" リストの検査、code の整合性チェック、スコア数値チェック。無効なレスポンスはスキップして処理継続（フェイルセーフ）。
    - DuckDB の executemany に対する互換性対策（空リストの扱いを考慮して条件分岐）。
    - テスト容易性: _call_openai_api をテスト用にモック差し替え可能。
    - 設計方針: datetime.today() を参照せず、全て呼び出し側から渡す target_date ベースで処理。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime テーブルに結果を書き込む。
    - マクロセンチメントは news_nlp の calc_news_window を使い、raw_news のマクロキーワードでフィルタした記事タイトルを LLM（gpt-4o-mini）に投げて評価。
    - LLM 呼び出しに対するリトライとフェイルセーフ（API 失敗時は macro_sentiment = 0.0）。
    - レジームスコアのクリッピングとラベリング（'bull' / 'neutral' / 'bear'）。
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で実装。書き込み失敗時には ROLLBACK を試みて例外を伝播。

- データ処理・ETL（kabusys.data）
  - ETL の公開インターフェース（etl.py）で ETLResult を再エクスポート。
  - pipeline モジュール（kabusys.data.pipeline）
    - 差分取得ロジック、バックフィル期間、品質チェック統合の設計。
    - ETLResult dataclass: 取得件数・保存件数・品質問題・エラー集約などを表現。has_errors / has_quality_errors / to_dict を提供。
    - DuckDB 操作ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - 市場カレンダーの調整ヘルパ（_adjust_to_trading_day など）を準備（実装途中の関数が存在）。

  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使った営業日判定ユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合は曜日ベースでフォールバック（週末を休業日扱い）。
    - calendar_update_job: J-Quants クライアント (jquants_client) を用いて差分取得 → 保存（バックフィル、健全性チェックを含む）。
    - 検索上限 (_MAX_SEARCH_DAYS)、先読み・バックフィル日数、健全性チェック（将来日付の異常検出）を実装。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から算出。データ不足時は None を返す。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 伝播に注意）。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を算出（EPS=0/欠損は None）。PBR/配当利回りは未実装。
    - 全関数は DuckDB SQL を駆使して高速に計算し、(date, code) ベースの辞書リストを返す。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（例: 1,5,21 営業日）の将来リターンをまとめて取得可能。horizons の検証あり。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装（ties の平均ランク処理含む）。有効レコードが 3 未満なら None を返す。
    - rank: 値を平均ランクに変換（小数丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ機能。

- その他
  - テスト/モックを意識した設計: OpenAI 呼び出しを差し替えられるエントリポイント（内部関数）を配置。
  - DuckDB のバージョン差（executemany の空引数など）に対する互換性処理を複数箇所で実装。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- DuckDB executemany に空リストを渡すと問題となる既知の挙動に対応するため、書き込み前に空リストチェックを追加（score_news 等）。
- JSON Mode における稀な前後余計テキスト混入に対して、最外の {} を抽出してパースを試みる復元ロジックを導入（news_nlp._validate_and_extract）。

### 破壊的変更（Breaking Changes）
- なし（初回リリース）。

### 既知の制限・注意点（Notes）
- OpenAI API キーが必須: score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY が未設定だと ValueError を送出します。
- 実運用での注文執行や kabu ステーションとの連携モジュール（strategy / execution / monitoring）は名前空間に準備されているが、今回のコードベースでの詳細実装は含まれていません（今後追加予定）。
- News/window の扱いは JST → UTC 変換を前提としており、raw_news.datetime が UTC で保存されている仕様に依存します。
- AI の出力に依存するため、LLM の振る舞い変化や API レスポンスの仕様変更に対しては破壊的ではないが運用上の注意が必要です（バージョン管理とテスト推奨）。
- データベースのスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提としています。スキーマが異なる場合はエラーになります。

### セキュリティに関する項目（Security）
- .env 自動ロード時に OS 環境変数を上書きしないデフォルト挙動を採用し、既存の OS 環境を protected として扱います。
- 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

---

今後のリリース予定（例）
- strategy / execution / monitoring の具体的な実装とテストカバレッジの追加
- J-Quants / kabu クライアントのエラーハンドリング強化とリトライ戦略の共通化
- AI レスポンス検証の強化（スキーマ検証・サニティチェック）とロギング改善

（必要であれば、各ファイルごとの変更点やコミット単位でのより詳細な履歴を生成できます。どの粒度で記載するか指示してください。）