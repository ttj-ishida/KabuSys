# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠。慣例によりバージョンは semver を使用します。

## [Unreleased]
- 特になし

## [0.1.0] - 2026-04-01
初回リリース。日本株のデータ取得・ETL・リサーチ・AIスコアリング・市場レジーム判定を目的とした基盤機能を実装。

### 追加 (Added)
- パッケージ初期化
  - パッケージ `kabusys` を公開。__all__ に ["data", "strategy", "execution", "monitoring"] を定義（モジュール構成のエントリポイント）。
  - バージョンを "0.1.0" として設定。

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準にルートを探索（__file__ 基準の探索により CWD に依存しない）。
  - .env パーサを実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォート有無で挙動を区別）
  - 自動ロードの無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを実装し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH, SQLITE_PATH
    - 監視関連: PID_FILE_PATH, CPU/MEMORY/DISK 閾値
    - 環境種別 (KABUSYS_ENV) と LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev のヘルパー

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar テーブル有無に応じた DB 優先ロジックと曜日ベースのフォールバック。
    - calendar_update_job を実装し、J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック含む）を提供。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを提供（取得件数・保存件数・品質チェック結果・エラー集約）。
    - 差分更新、バックフィル、品質チェック連携（jquants_client / quality との連携を想定）を設計。
  - etl モジュールで ETLResult を再エクスポート。

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp）:
    - raw_news + news_symbols から時間ウィンドウ（前日15:00 JST〜当日08:30 JST）に基づき記事を集約。
    - 銘柄ごとに最大記事数・文字数でトリムし、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信。
    - バッチサイズ、リトライ（429/ネットワーク断/5xx）・指数バックオフ実装。
    - レスポンスの堅牢な JSON パース・バリデーション（results配列、code/score 検証、未知コードは無視）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - テスト容易性のため _call_openai_api のパッチ差替えを想定。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily/raw_news 参照、OpenAI 呼び出し（gpt-4o-mini）を行い、レスポンス失敗時は macro_sentiment を 0.0 にフォールバック。
    - レジームスコア計算と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出しは news_nlp 側と意図的に独立した実装（モジュール結合を避ける）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離の計算（データ不足時は None）。
    - calc_volatility: 20日 ATR, 相対ATR, 20日平均売買代金, 出来高比を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算。
    - DuckDB を使用した SQL + Python 実装で外部 API への影響なし。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランク扱いのランク変換実装（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median の統計要約を算出。
  - データ側の正規化ユーティリティ zscore_normalize を再エクスポート。

- 共通・運用改善
  - DuckDB を主要な分析 DB として利用する設計。
  - ルックアヘッドバイアス防止の設計指針を徹底（datetime.today()/date.today() を直接参照しない関数設計、クエリで date < target_date などの排他条件）。
  - DB トランザクション失敗時のロールバック処理とログ出力を実装。
  - ロギング（logger）を各モジュールに導入し情報・警告・例外の追跡を容易化。
  - テスト容易性を意識した設計（API 呼び出しの差し替え、sleep 関数注入、引数で API キー注入など）。

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 環境変数読み込みの堅牢化:
  - .env のクォート・エスケープ・コメント処理を改善し、より多様な .env フォーマットに対応。
  - .env.local を上書き (.env を base に .env.local で override) する優先度ルールを実装。
  - OS 環境変数は protected として .env による意図しない上書きを防止。

- OpenAI API 呼び出しの堅牢化:
  - RateLimitError / APIConnectionError / APITimeoutError / 5xx の場合にリトライを実装し、最終的な失敗時は安全なデフォルト（0.0）にフォールバック。
  - レスポンス JSON パース失敗時の復元ロジックを実装（文字列内の最外の {} を抽出してパースを試みる）。

- DB 書き込みの安全化:
  - ai_scores / market_regime への書き込みは対象コードを絞って DELETE → INSERT を行うことで部分失敗時に既存データを保護。
  - DuckDB の executemany 空リスト制約に対するガードを追加（空の場合は実行をスキップ）。

### 非推奨 (Deprecated)
- 該当なし

### 削除 (Removed)
- 該当なし

### セキュリティ (Security)
- OpenAI API キー管理:
  - OpenAI 呼び出しには api_key 引数または環境変数 OPENAI_API_KEY を要求。未設定時は ValueError を送出して明示的に失敗させる（誤動作を防止）。
- .env 自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト/CI 用の安全対策）。
- .env から OS 環境変数を上書きしないための保護（protected set）を実装。

### 注意事項 / 既知の設計上の旨（Notes）
- すべての日付処理は timezone を混入させないため date / UTC naive datetime を扱う方針。ニュースウィンドウ等は JST→UTC 変換をコード内で明示的に行う。
- OpenAI との連携は外部 API であり、API 仕様（ステータスコードやレスポンス形式）の将来的な変更に対しては SDK 互換性の確認が必要。
- DuckDB のバージョン差異によるバインド挙動（配列バインド等）に配慮した実装を行っている。
- 初期リリースのため、運用上の監視・フォールトトレランスや大規模データ最適化は今後の改善点。

---

（今後のリリースでは各モジュールの API 変更・パフォーマンス改善・追加の品質チェックや監視機能の拡張などを記載していきます。）