# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
バージョン付けは https://semver.org/ に従います。

## [0.1.0] - 2026-03-28

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - top-level エクスポート: data, strategy, execution, monitoring
- 環境設定モジュール（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロードを実装（優先順: OS > .env.local > .env）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .git または pyproject.toml を起点にプロジェクトルートを探索する実装により、CWD に依存しない読み込み。
  - .env パーサーの実装:
    - export KEY=val 形式対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、コメント処理（クォートなし時の '#' 処理）。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。
  - デフォルト値や必須環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（valid: development, paper_trading, live）
    - LOG_LEVEL（valid: DEBUG, INFO, WARNING, ERROR, CRITICAL）
- AI 関連モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news / news_symbols からニュースを収集して、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとにセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む。
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチ処理: 最大 20 銘柄／リクエスト、1銘柄あたり最大 10 記事・3000 文字にトリム。
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（設定: _MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - レスポンス検証: JSON パース耐性（前後余計テキストの { } 抽出）、"results" リスト形式の検証、未知コードや非数値スコアは無視。
    - スコアは ±1.0 にクリップ。
    - 書き込みは冪等（DELETE → INSERT）で部分失敗時に他銘柄スコアを保護。
    - テスト容易性: API 呼び出し関数は内部で分離（unittest.mock.patch で差し替え可能）。
  - regime_detector.score_regime:
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等で書き込む。
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、データ不足時は中立（1.0）を採用。
    - マクロ記事はキーワードフィルタで抽出し、OpenAI に JSON 出力を要求して macro_sentiment を取得。API 失敗時は macro_sentiment=0.0（フェイルセーフ）。
    - レジーム合成・閾値設定（_MA_WEIGHT, _MACRO_WEIGHT, _BULL_THRESHOLD, _BEAR_THRESHOLD）およびリトライ処理を実装。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等化。
- データ基盤モジュール（kabusys.data）
  - calendar_management:
    - market_calendar テーブルを用いた営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB にデータがない場合は曜日ベースのフォールバック（土日非営業日）。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を更新する夜間バッチ処理（バックフィル・健全性チェックを実装）。
  - pipeline / ETL:
    - ETLResult データクラスを追加（取得数、保存数、品質問題、エラー一覧等を保持）。
    - 差分取得、保存（idempotent）、品質チェックの設計方針を実装（モジュール化・ロギング）。
  - etl モジュールは ETLResult を再エクスポート。
- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: EPS から PER、ROE を raw_financials と prices_daily から算出。
    - 全関数は DuckDB 上で SQL を使って実行し、(date, code) ベースの辞書リストを返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（例: 1, 5, 21 営業日）先のリターンを計算。ホライズンの妥当性チェックあり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を算出。
    - rank: 値リストを同順位を平均ランクとするランクに変換。
    - factor_summary: ファクター列ごとの count/mean/std/min/max/median を計算。
  - research パッケージは主要関数を __all__ で公開（zscore_normalize は data.stats から再利用）。
- 実装上の注意点（全体）
  - ルックアヘッドバイアス防止のため、内部処理で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - DuckDB を主要な分析用 DB として利用。
  - エラー・例外はログに残し、API 失敗時にもシステム全体が停止しないフェイルセーフな挙動を旨とする。
  - テスト容易性を考慮した設計（API 呼び出し箇所の差し替え）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種トークンは Settings 経由で環境変数から取得する設計。必須トークン未設定時は明確な ValueError を発生させることで、秘密情報の取り扱いミスを早期に検出。

---

今後のリリースでは以下のようなトピックを想定しています（例）:
- strategy / execution / monitoring パッケージ実装の追加（実際の売買戦略・注文実行・モニタリング連携）。
- J-Quants / kabu API クライアントの詳細実装と認証フローの追加。
- テストカバレッジ拡張、CI 統合、型チェック強化およびドキュメント整備。