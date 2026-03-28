# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
  
*リンク:* https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開。

### 追加
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開インターフェースを定義（data, strategy, execution, monitoring を __all__ に登録）。

- 設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。
    - ロード優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - OS 環境変数を保護する protected 機能（既存キーを上書きしない）。
  - .env パーサーの実装:
    - export prefix 対応、シングル/ダブルクォート対応、バックスラッシュエスケープの解釈、インラインコメントの扱い（クォートの有無で挙動を分離）。
  - Settings クラスを提供:
    - J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルのプロパティを定義。
    - 必須環境変数未設定時は明確な ValueError を発生させる（ユーザー向けメッセージ付き）。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar テーブルを扱う）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - 夜間バッチ更新 job (calendar_update_job): J-Quants から差分取得 → 冪等保存（ON CONFLICT）。バックフィル・健全性チェック実装。
    - カレンダーデータがない場合の曜日ベースフォールバック実装（最大探索日数制限あり）。
  - ETL / pipeline:
    - ETLResult データクラスを公開（ETL 実行結果のサマリ）。
    - 差分取得、保存（idempotent）、品質チェック（quality モジュール連携）の設計に基づく基盤を実装。
    - DuckDB での最大日付取得、テーブル存在チェック等のユーティリティを実装。
    - backfill 日数やカレンダーの先読み等のデフォルト設定を提供。

- AI / NLP (kabusys.ai)
  - news_nlp:
    - raw_news / news_symbols を元に銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出して ai_scores に書き込む。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチ呼び出し（最大 20 コード/チャンク）、1銘柄あたり記事数と文字数上限（トリム）を実装。
    - OpenAI レスポンスのバリデーションと抽出を厳格化（JSON mode を期待、余分な前後テキストの復元ロジックあり）。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。失敗時はフェイルセーフでスキップ。
    - テスト容易性: _call_openai_api を patch して置換可能。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とニュース LLM センチメント（重み30%）を組み合わせ、市場レジーム（bull/neutral/bear）を算出して market_regime テーブルに冪等書き込み。
    - MA 計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを防止。
    - LLM 呼び出しは独立実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 冪等性を考慮した DB トランザクション（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- リサーチ (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M）、200日MA乖離、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高変化率）、バリュー（PER/ROE）計算関数を実装。
    - DuckDB に依存した SQL を中心に実装。データ不足時の None ハンドリングあり。
  - feature_exploration:
    - 将来リターン算出（指定ホライズンの LEAD を用いた取得）、IC（Spearman ランク相関）の計算、ランク関数（同順位は平均ランク）、ファクター統計サマリ（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結する設計。

### 変更
- 初回リリースのため過去変更なし。

### 修正
- 初回リリースのため対象なし。

### 既知の注意点 / 設計上のポイント
- ルックアヘッドバイアス防止:
  - AI モジュールおよびリサーチ関数は datetime.today()/date.today() を内部で参照せず、必ず target_date を引数として受け取り、その日以前のデータのみを利用する設計。
- OpenAI 連携:
  - gpt-4o-mini を想定し JSON Mode を利用。API キーは api_key 引数または環境変数 OPENAI_API_KEY で渡す必要あり。
  - テスト容易性のため _call_openai_api をモック可能にしている。
- DB 書き込みの冪等性:
  - ai_scores / market_regime / market_calendar 等への書き込みは既存行を削除してから挿入する方式で部分失敗時の保護を実施。
- 環境変数処理:
  - .env の読み込みはプロジェクトルート検出に成功した場合にのみ自動実行。OS 環境変数の上書きを防止する protected 機能有り。
  - 必須トークン（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings のプロパティアクセス時にチェックされ、未設定なら ValueError を発生させる。
- DuckDB の互換性配慮:
  - executemany に空リストを渡せないバージョンへの対応（空チェックを行ってから executemany を呼ぶ）。
- リトライ戦略:
  - news_nlp と regime_detector の両方で 429/ネットワーク/タイムアウト/サーバー5xx を対象に指数バックオフを実装（最大試行回数は定数で管理）。

### セキュリティ / 必要な設定
- 実行に必須の環境変数:
  - OPENAI_API_KEY（AI モジュール）、JQUANTS_REFRESH_TOKEN（J-Quants API）、KABU_API_PASSWORD（kabu API）、SLACK_BOT_TOKEN/SLACK_CHANNEL_ID（通知）。
- 外部依存:
  - openai Python SDK（v1 系想定）、duckdb、およびプロジェクト内で想定される jquants_client 等のクライアントモジュール。

### 破壊的変更
- 初回リリースのため該当なし。

---

（補足）この CHANGELOG はコードベースから推測して作成しています。実際のリリース手順やパッケージ配布時には日付・バージョン、依存関係のバージョン固定、追加のセキュリティ注意事項などを合わせて更新してください。