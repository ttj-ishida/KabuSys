# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

すべての注記は、ソースコードから推測できる実装仕様・挙動に基づいて作成されています。

## [Unreleased]

## [0.1.0] - 初回リリース
初期リリース。日本株自動売買システム "KabuSys" のコアモジュール群を公開。

### 追加 (Added)
- パッケージ初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__ にてエクスポート）

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動ロードする仕組みを実装。
  - 自動ロードを無効にするフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）
  - .env の読み込み優先順位: OS 環境変数 > .env.local（上書き） > .env（非上書き）
  - 必須環境変数取得ヘルパ: _require()
  - Settings クラスを公開（settings インスタンス経由）
    - 必須設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意/デフォルト: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH、SQLITE_PATH
    - 環境種別検証: KABUSYS_ENV は development / paper_trading / live のいずれかを強制
    - ログレベル検証: LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可
    - ヘルパプロパティ: is_live / is_paper / is_dev

- ニュース NLP & レジーム判定 (kabusys.ai)
  - news_nlp.score_news
    - raw_news / news_symbols を集約し、銘柄ごとのニューステキストを OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む。
    - 処理時間ウィンドウ（JST 前日15:00〜当日08:30）を UTC に変換して比較する calc_news_window を提供。
    - バッチ処理: 最大 20 銘柄／リクエスト、1銘柄あたり最大記事数・最大文字数でトリム。
    - JSON Mode 応答のバリデーションを実装し、スコアを ±1.0 にクリップ。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ実装。
    - 部分成功に配慮した DB 書き込み（対象コードのみ DELETE → INSERT）を実装。
    - テスト容易性のため OpenAI 呼び出し箇所はパッチ可能（_call_openai_api の差し替えを想定）。
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime に冪等書き込み。
    - マクロキーワードで raw_news から記事を抽出、OpenAI（gpt-4o-mini）で評価（JSON 出力期待）。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 とするフォールバック（フェイルセーフ）。
    - ルックアヘッドバイアス防止（内部で datetime.today() を直接参照しない、prices_daily クエリは date < target_date 等で排他）。
    - API レート制限や接続エラーに対するリトライとログ出力を実装。

- データプラットフォーム (kabusys.data)
  - ETL
    - data.pipeline.ETLResult を公開（ETL 実行結果の構造化、品質問題・エラー集約）。
    - 差分更新・バックフィル・品質チェックのための設計（ソースコードに注釈あり）。
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを使用した営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job（J-Quants から差分取得して保存）を実装。
    - DB 登録値優先、未登録日は曜日ベース（週末フォールバック）で決定する一貫性のある挙動。
    - カレンダー取得時にバックフィル（日次の差分再取得）・健全性チェックを実施。
    - _MAX_SEARCH_DAYS による無限ループ防止。
  - jquants_client / quality 等のクライアント・品質チェック呼び出しを前提とした実装（実装ファイルは参照されるが、本 CHANGELOG はコード内容からの推測に基づく）。

- リサーチ機能 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（prices_daily を参照、データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - 設計上、DuckDB SQL を多用し外部 API に依存しない実装。
  - feature_exploration
    - calc_forward_returns: 指定日基準で複数ホライズンの将来リターンを一括取得可能（デフォルト [1,5,21]）。
    - calc_ic: Spearman（ランク）相関（IC）計算の実装（結合・None 排除・最小サンプル数チェック）。
    - rank: 同順位は平均ランク化するランク付けユーティリティ（丸めによる ties 対応）。
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）を計算。

### 変更 (Changed)
- 初回リリースにより既存ライブラリとの互換性に配慮した実装方針を採用（DuckDB を主要 DB として想定、外部依存の最小化）。

### 修正 (Fixed)
- 該当なし（初版公開のため特定の不具合修正履歴はなし。コード内に各種フォールバック・例外処理が含まれているため、堅牢性が考慮されています）。

### セキュリティ (Security)
- 機密情報は環境変数で管理する方針を明記（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、OPENAI_API_KEY）。
- .env 自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入。
- OpenAI API キーは引数注入も可能で、テストでの差し替えやキー漏洩リスク低減に対応。

### 注意事項 / 実装上の設計ノート
- ルックアヘッドバイアス対策として、日付参照はすべて呼び出し元が渡す target_date に依存する設計（内部で date.today()/datetime.today() を参照しない関数が多い）。
- OpenAI 呼び出し部は JSON mode を期待したレスポンス処理を行うが、レスポンスに付随する前後の余計なテキストに対しても復元ロジックを用意。
- DB 書き込みは冪等性を意識（DELETE → INSERT、トランザクションおよび ROLLBACK 処理を実装）。
- テスト容易性のため、外部 API 呼び出し（OpenAI 等）をモック可能なように設計（モジュール内の _call_openai_api を差し替え）。
- DuckDB のバージョン依存（executemany の空リスト不可等）への配慮が随所にあり、互換性と安全性を優先した実装。

---

(注) 上記はリポジトリ内のソースコードから読み取れる仕様・設計・挙動を基に作成した CHANGELOG です。実際のリリースノートやユーザー向けのドキュメントを作成する場合は、さらに変更理由、既知の制約、互換性情報、使用例や設定手順（.env.example 等）を追記してください。