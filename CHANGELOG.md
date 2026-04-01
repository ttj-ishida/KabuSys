# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、日本語で記載しています。

注意: この CHANGELOG はリポジトリの現在のコードベース（v0.1.0）から推測して作成した初期リリースの要約です。実際のコミット履歴ではなく、コード内のドキュメント文字列・実装から導出した機能・設計上のポイントをまとめています。

Unreleased
---------

（なし）

[0.1.0] - 2026-04-01
-------------------

Added
- 基本パッケージ情報
  - パッケージ名 kabusys とバージョンを `src/kabusys/__init__.py` にて v0.1.0 として定義。

- 環境設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を起点に行い、CWD に依存しない実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` の読み込みは上書き制御（override）や OS 環境変数保護（protected keys）に対応。
    - `.env` のパースは export プレフィックス、クォート、エスケープ、インラインコメントに対処する堅牢な実装。
  - 必須設定項目を取得するヘルパー `_require` と、アプリケーション設定を表す `Settings` クラスを提供。
    - 主要な設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 呼び出し時に参照）
    - デフォルト DB パス: duckdb → `data/kabusys.duckdb`、sqlite → `data/monitoring.db`
    - 監視用しきい値（CPU/MEM/ディスク）や pid ファイルパスの設定プロパティを提供
    - 環境（KABUSYS_ENV）やログレベル（LOG_LEVEL）の検証（許容値チェック）を実装

- AI 関連モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）に JSON モードで投げてセンチメントスコア（-1.0〜1.0）を取得。
    - 時間ウィンドウは JST 基準で「前日 15:00 〜 当日 08:30」を対象。UTC に変換して DB と照合する `calc_news_window` を提供。
    - バッチ処理（最大 20 銘柄／コール）、1 銘柄あたりの記事・文字数上限（記事数:10、文字数:3000）などトークン肥大化対策を実装。
    - API 呼び出しはリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装し、失敗時はスキップしてフェイルセーフ（例外を上げず続行）。
    - レスポンスの堅牢なバリデーション（JSON 抜き出し、results リスト、code と score の検査、スコアの数値化・クリップ）を実装。
    - DuckDB への書き込みは「DELETE（対象コード）→ INSERT」を用いて部分失敗時に既存データを保護。
    - テスト容易性のため、内部 API 呼び出し関数を patch できる設計を提供（_call_openai_api をモック可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロキーワードで raw_news をフィルタし、最大 20 記事を LLM に渡して macro_sentiment を算出。
    - LLM 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）で、リトライ・バックオフ・エラー時のフォールバック macro_sentiment=0.0 を採用。
    - レジームはスコアをクリップして閾値でラベル付けし、DuckDB の market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）に保存。
    - Look-ahead バイアス防止のため内部処理で date.today()/datetime.today() を直接参照せず、target_date ベースで動作。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーの保持・更新ロジックを実装（market_calendar テーブル参照）。
    - 営業日判定・翌営業日/前営業日取得・期間内営業日リスト取得・SQ日判定などのユーティリティを提供。
    - DB にデータがない場合は曜日ベース（平日を営業日）でフォールバックする堅牢性を確保。
    - 夜間バッチ更新ジョブ calendar_update_job を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル・健全性チェックを実装）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を表すデータクラス ETLResult を実装し、fetch/save の数や品質チェック結果・エラーを収集・表現可能に。
    - 差分更新、backfill、品質チェックの設計方針を反映（実装の一部：API 呼び出し・テーブル存在チェック・最大日付取得ロジックなど）。
    - `kabusys.data.etl` で ETLResult を公開（再エクスポート）するインターフェースを追加。
  - jquants_client / quality 等のクライアント利用を前提とした設計（詳細実装はクライアント側に委譲）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比）およびバリュー（PER、ROE）などの定量ファクターを算出する関数群を実装。
    - DuckDB 上で SQL ウィンドウ関数を活用して効率よく計算。データ不足時は None を返すなど堅牢な振る舞い。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: target_date から複数ホライズン先のリターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を計算し、必要件数未満は None を返す。
    - 統計サマリー（factor_summary）やランク付けユーティリティ（rank）を実装。
  - 研究用ユーティリティとして zscore_normalize を data.stats から再利用可能に公開。

Other notable implementation / design decisions
- DuckDB を主要なローカル分析 DB として利用。SQL と Python を併用し、高速にデータを集計する設計。
- API（OpenAI / J-Quants 等）呼び出しに対しては:
  - 明示的なリトライ・指数バックオフ（429、ネットワーク断、タイムアウト、5xx 等）。
  - 失敗時にフェイルセーフ（例外を上位へ伝播させず継続）する箇所を多用し、運用中の部分的障害に耐性を持たせる設計。
- テスト支援:
  - 内部の API 呼び出しポイント（_kabusys.ai.*._call_openai_api など）をモック可能な形で分離。
- 安全性 / 一貫性:
  - DB 書き込みは冪等化（DELETE → INSERT / ON CONFLICT）を意識した実装。
  - DuckDB の executemany に関する挙動（空リスト不可）を考慮したガードを実装。

Known limitations / Notes
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY の指定が必須（未設定時は ValueError が発生）。
- ニュース/レジーム系処理は LLM のレスポンスや外部 API に依存するため、運用時のコスト・レイテンシに注意が必要。
- 一部モジュールの実装はファイル末尾が切れている（pipeline モジュールの最後で切断された形跡あり）。実運用前に該当箇所の確認を推奨。
- デフォルトパスや閾値は設定により上書き可能（Settings による管理）。

Security
- 特記事項なし（現コード内に秘密情報の直書きはなし）。ただし、環境変数（API キー等）の管理は運用上の注意が必要。

---

この CHANGELOG はコード内の docstring / 実装ロジックから機能を要約したものであり、コミット単位の差分ではありません。より詳細な変更履歴（個別コミットや issue 対応など）を反映する場合は、実際の Git ログと合わせて更新してください。