# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-03

### 追加 (Added)
- 初期リリース: KabuSys — 日本株自動売買システムのコアライブラリを公開。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に "data", "strategy", "execution", "monitoring" を公開（ルートパッケージ）。
- 環境設定モジュール (kabusys.config)
  - .env ファイルおよび環境変数の読み込み機能を提供。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に自動探索（CWD 非依存）。
  - .env / .env.local の読み込み順序管理（OS 環境変数優先、.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - 詳細な .env パース実装: export プレフィックス対応、引用符内のバックスラッシュエスケープ、インラインコメント処理等。
  - Settings クラスを提供し、各種必須設定やデフォルト（DB パス・しきい値等）を公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須参照支援。
    - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等のデフォルトパス。
    - KABUSYS_ENV / LOG_LEVEL 等のバリデーション（許容値チェック）。
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に対応する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事トリム（最大記事数・文字数）によるトークン肥大対策。
    - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、その他はスキップで継続。
    - レスポンスバリデーション: JSON 抽出/パース、results 配列・code/score の検証、score の数値変換・有限性チェック、±1.0 でクリップ。
    - 部分失敗時に既存スコアを保護するため、書き込みは対象コードのみ DELETE → INSERT の冪等更新。
    - テスト容易性: _call_openai_api の差し替え（unittest.mock.patch を想定）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ書き込み。
    - マクロキーワードフィルタで raw_news から記事を抽出し、OpenAI で macro_sentiment を取得。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフ。計算はルックアヘッドバイアスを避ける実装。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクションのロールバック処理。
- データモジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API。
    - market_calendar が未登録時は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・健全性チェック付きで market_calendar を更新する処理を提供。
  - pipeline / etl:
    - ETLResult データクラスを定義（取得/保存レコード数、品質問題、エラー履歴等を収集）。
    - pipeline モジュールの ETLResult を etl パッケージで再エクスポート。
    - ETL の設計方針（差分取得、バックフィル、品質チェックの集約）を実装の前提として明記。
- リサーチモジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等の計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等。
    - calc_value: PER / ROE を raw_financials と prices_daily を基に算出。
    - すべて DuckDB SQL を主体に計算し、(date, code) 単位の dict リストを返す。
  - feature_exploration:
    - calc_forward_returns: 将来リターン計算（任意ホライズン。horizons の妥当性チェックあり）。
    - calc_ic: スピアマン（ランク）相関で IC を計算（欠損/同順位/records 少数時の扱いを考慮）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクを返す実装（丸めで ties 検出の安定化）。
- テスト/デバッグ向けの設計上の配慮
  - OpenAI 呼び出し関数をモジュール内で独立実装しており、テスト時に差し替え可能。
  - 環境自動ロード制御（KABUSYS_DISABLE_AUTO_ENV_LOAD）により CI/ユニットテストでの副作用を防止可能。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 削除 (Removed)
- （初期リリースのため該当なし）

### 非推奨 (Deprecated)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キー等の秘密情報は環境変数で管理するよう設計。
- 環境変数未設定時、明示的な ValueError を返して早期に検出されるようにしている（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
- .env の読み込みは自動だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化できる。

### 互換性・移行上の注意 (Migration)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（AI 機能を使用する場合）
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- monitor / execution 等のデーモン的機能で使用するファイル:
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
- DuckDB 側の期待テーブル（このバージョンで参照／更新されるテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials
- OpenAI の出力は JSON mode を前提にしているが、JSON 外の余計な文字列が混入するケースに備えた復元ロジックを持つため、致命的なパース失敗時は該当チャンクをスキップする（フェイルセーフ）。

### 既知の制限 (Known issues)
- OpenAI レスポンスの不整合（期待外の JSON 形式）や API 長時間障害時は該当チャンクをスキップする設計のため、部分的にスコアが取得できない可能性がある。
- DuckDB の executemany に空リストを渡すと失敗するバージョン依存の挙動へ対応するため、明示的に空チェックを行っている（挙動は使用する DuckDB バージョンに依存）。
- news_nlp の出力スコアと regime_detector の macro_sentiment は現在同一レンジだが、将来的にスケーリング変更の可能性あり。

---

今後のリリースでは以下を検討中:
- strategy / execution / monitoring モジュールの実装・公開（発注・バックテスト・監視ロジック）。
- ai モジュールのモデル差し替え・ローカル LLM 対応・コスト最適化。
- ETL の自動スケジューリングおよびより詳細な品質レポート。

もし CHANGELOG に追加してほしい事項（例: 日付修正、特定コミットの追記、リリースノートの細分化）があれば教えてください。