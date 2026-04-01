# Changelog

すべての重要な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。  

なお、本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-04-01

初回リリース。KabuSys のコア機能群を実装しました。主にデータ取得/ETL、マーケットカレンダー管理、ファクター計算、ニュース系 AI スコアリング、環境設定まわりのユーティリティを含みます。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化: `kabusys.__init__` を提供。公開サブパッケージ: data, strategy, execution, monitoring。
  - バージョン: `__version__ = "0.1.0"`。

- 設定管理 (`kabusys.config`)
  - 環境変数読み込み機能を実装（.env / .env.local をプロジェクトルートから自動読み込み、CWD 非依存）。
  - .env パーサーは以下をサポート:
    - 空行・コメント（#）の無視、`export KEY=val` 形式対応、
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理、
    - クォートなし行のインラインコメント判定（直前が空白/タブの場合のみ）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入。
  - 必須環境変数取得ヘルパ `_require` と、アプリケーション設定 `Settings` クラスを実装。
  - `Settings` に以下の設定アクセスプロパティを実装:
    - J-Quants, kabuステーション, Slack, データベースパス（DuckDB/SQLite）、監視閾値、環境（development/paper_trading/live）とログレベル検証等。
  - 環境値のバリデーションを実装（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。

- AI（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp`:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを評価する `score_news` を実装。
    - タイムウィンドウ計算（JST 基準 → DB の UTC 比較）、1銘柄あたりの文字数・記事数トリム、最大バッチサイズ、JSON Mode のレスポンスバリデーション、スコアの ±1.0 クリップ、DuckDB への冪等書き込み（DELETE→INSERT）をサポート。
    - ネットワークリトライ（429/タイムアウト/5xx）を指数バックオフで行う実装。
    - レスポンスパースの堅牢化（不正な前後テキストから最外の JSON を抽出する試み等）。
  - `kabusys.ai.regime_detector`:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成し、日次の市場レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
    - MA200 比率計算（ターゲット日未満データのみ使用、データ不足時は中立扱い）、マクロキーワードによるニュース抽出、OpenAI 呼び出し（独立実装）、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）、結果の冪等的な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。

- リサーチ / ファクター計算 (`kabusys.research`)
  - `factor_research`:
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（データ不足時は None）。
    - ボラティリティ/流動性: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - バリュー: 最新の raw_financials から PER（EPS が 0/欠損時は None）、ROE を計算。
    - 全関数は DuckDB の `prices_daily` / `raw_financials` を参照し、外部 API へアクセスしない設計。
  - `feature_exploration`:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ρ）計算、ランク付けユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部依存を使わず標準ライブラリで実装。
  - `research.__init__` で主要関数を再エクスポート。

- データプラットフォーム (`kabusys.data`)
  - カレンダー管理 (`calendar_management`):
    - JPX カレンダー（market_calendar）を参照する営業日判定ロジック: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を実装。
    - DB にデータがない場合は曜日ベース（平日）でフォールバックする一貫した振る舞い。
    - 夜間バッチ更新 `calendar_update_job` を実装（J-Quants API から差分取得、バックフィル、健全性チェック、保存処理）。
  - ETL / パイプライン (`pipeline`, `etl`):
    - ETL の結果を表す `ETLResult` dataclass を実装（取得数／保存数／品質問題／エラー一覧などを含む）。
    - 差分取得・バックフィル・品質チェックの方針を採用する設計。
    - `etl.py` で `ETLResult` を再エクスポート。
  - DuckDB 周りの互換性考慮:
    - executemany に空リストを渡せない DuckDB 0.10 の制約を考慮した実装（空チェックを挿入）。
    - 日付型の安全な変換ユーティリティを提供。

- その他
  - ロギングを多用し、警告・例外時に詳細を出力する設計。
  - OpenAI クライアント呼び出し箇所はテストで差し替えられるよう内部関数を分離（unittest.mock.patch 想定）。

### 変更 (Changed)
- 初版リリースのため該当なし。ただし設計上の重要ポイントを明確化:
  - ルックアヘッドバイアス対策として各アルゴリズムは内部で現時点の datetime.date を直接参照せず、呼び出し側が `target_date` を渡す方式を採用。
  - LLM 呼び出しは JSON Mode を利用し、厳密な JSON 出力を期待するが、パース耐性を持たせる実装（余分な前後テキストのトリミング）。

### 修正 (Fixed)
- 初版リリースのため該当なし（実装内で多数のフォールバック/エラーハンドリングを追加して安定性を向上させています）。

### 既知の制限 / 注意点 (Known issues / Notes)
- OpenAI SDK に依存（OpenAI クライアントの API 仕様変更があった場合、呼び出し部分の更新が必要）。
- DuckDB バージョンによる振る舞い差（executemany の空リスト扱い等）に注意。実装は互換性を考慮しているが、稀な DB バージョン差異が出る可能性あり。
- news_nlp / regime_detector は外部 API（OpenAI / J-Quants）を使うため、API キー未設定時は ValueError を投げる。CI/テストではモックを利用してください。
- 時刻/タイムゾーン:
  - ニュースウィンドウは説明のとおり JST 基準で計算し、DB の datetime は UTC（naive）で比較する前提。DB 側の timestamp 格納形式に依存するため取り扱いに注意。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。配布後や特殊な配置では自動ロードを無効化して環境変数を明示的に設定することを推奨。

### 必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（OpenAI 呼び出しを行う場合）など。詳細は `kabusys.config.Settings` を参照。

---

今後のリリースでは、戦略・実行・監視サブパッケージ（strategy, execution, monitoring）の実装拡張、テストカバレッジの強化、外部クライアントラッパの安定化、OpenAI 呼び出しの抽象化改善（コスト管理や代替モデル対応）等を予定すると良いでしょう。