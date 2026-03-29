# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、このCHANGELOGはリポジトリ内のコードを解析して推測に基づき作成しています（初回リリース想定）。

## [0.1.0] - 2026-03-29

### 追加 (Added)
- パッケージ初期リリース: kabusys — 日本株自動売買システムのコアモジュール群を追加。
  - パッケージ公開バージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。

- 環境設定/読み込み (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装:
    - コメント行・空行スキップ、`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理やインラインコメントの扱いに対応。
  - _load_env_file による保護キー（OS 環境変数を上書きしない）ロジックを実装。
  - Settings クラスを提供し、環境変数の必須チェック（_require）や既定値、型変換を行うプロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須チェック
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証
    - データベースパス（duckdb/sqlite）の Path 変換
    - is_live / is_paper / is_dev のユーティリティ

- AI モジュール (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）へバッチで送信してセンチメントを算出。
    - タイムウィンドウ計算 (calc_news_window): JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換して扱う設計。
    - バッチサイズ、記事件数・文字数上限（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によるトークン肥大化対策。
    - OpenAI 呼び出しの冪等的リトライ、429/ネットワーク断/タイムアウト/5xx で指数バックオフ、失敗時はスキップして継続（フェイルセーフ）。
    - JSON Mode を利用しレスポンスを厳密にバリデートして ai_scores テーブルへ置換（DELETE → INSERT）の方式で書き込み。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch でモック可能）。
    - score_news(conn, target_date, api_key=None) を公開：戻り値は書き込んだ銘柄数。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM, 重み 30%）を合成して日次でレジーム（bull / neutral / bear）判定。
    - マクロ記事抽出は内部で定義したキーワード群に基づいて raw_news からタイトルを取得。
    - OpenAI 呼び出し（_MODEL=gpt-4o-mini）で JSON をパースし macro_sentiment を算出、API失敗時は 0.0 にフォールバック。
    - リトライ／バックオフ／HTTP 5xx の扱いを明確化。レスポンスパース失敗時は 0.0 を採用して処理継続。
    - レジームスコア合成後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。
    - score_regime(conn, target_date, api_key=None) を公開：成功時に 1 を返す。OpenAI API キー未設定時は ValueError。

- データ関連モジュール (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を基にした営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未取得時は曜日（土日）ベースでフォールバックする堅牢な設計。
    - next/prev_trading_day は DB 登録値を優先し、未登録日は曜日ベースのフォールバック。探索上限（_MAX_SEARCH_DAYS）を設定して無限ループを防止。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants から差分取得して保存、バックフィル、健全性チェック対応。

  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult dataclass を公開（etl.py では ETLResult を再エクスポート）。
    - 差分取得、保存（jquants_client を利用した idempotent な保存）、品質チェック（quality モジュールを利用）の設計方針を実装。
    - テーブル存在チェック、最大日付取得ユーティリティ、バックフィル日数等の実装を含む。
    - ETLResult.to_dict() で品質問題をシリアライズ可能。

  - その他: data パッケージは jquants_client, quality 等（インテグレーション先）を前提。

- 研究 / リサーチモジュール (src/kabusys/research)
  - factor_research (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER/ROE）などの計算関数を実装。
    - DuckDB での SQL ウィンドウ関数を中心に実装し、外部 API にアクセスしない安全設計。
    - calc_momentum / calc_volatility / calc_value を公開し、(date, code) ベースの dict リストを返す。
    - データ不足時の挙動（必要行数未満で None を返す等）を明記。

  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - スピアマンランク相関を独自実装（ties は平均ランクで処理）、必要レコード数不足時は None。
    - pandas 等に依存しない純粋 Python 実装。

- 共通・運用上の配慮
  - DuckDB を主なローカル分析 DB として採用（各モジュールは DuckDB 接続を引数で受ける設計）。
  - いずれの分析処理も look-ahead バイアスを避ける設計（datetime.today() / date.today() を直接参照しない、明示的な target_date を採用）。
  - OpenAI 呼び出しには JSON Mode を利用し、レスポンスは厳密にパース・バリデーションすることでモデル出力のブレを軽減。
  - ロギングを各モジュールで活用（警告・情報ログによりフェイルセーフ状態や状況を明示）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記:
- この CHANGELOG はリポジトリ内のコードから仕様や設計方針を推測してまとめています。実際のリリースノートとして使用する場合は、変更理由や実装者、影響範囲、移行手順などをプロジェクトの運用ポリシーに従って追記してください。