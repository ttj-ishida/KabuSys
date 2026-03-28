# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

※初回リリース（パッケージ版 v0.1.0）として、実装済みの主要機能と設計上の注意点を記載しています。

## [0.1.0] - 2026-03-28

### Added
- パッケージ基盤
  - kabusys Python パッケージを追加。パッケージの公開バージョンは `0.1.0`。
  - パッケージトップのエクスポート: data, strategy, execution, monitoring（__all__）。

- 環境設定・ロード機能（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出: `.git` または `pyproject.toml` を基準に探索（CWD に依存しない）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env の読み込み時は既存 OS 環境変数（protected set）を保護しつつ、`.env.local` による上書きをサポート。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用可能。
  - 設定アクセス用 `Settings` クラスを提供（プロパティ例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）と必須項目チェック（未設定時 ValueError）。

- データ (kabusys.data)
  - カレンダー管理（calendar_management）
    - JPX カレンダー（market_calendar）管理と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値を優先し、未登録日は曜日ベース（週末）でフォールバックする一貫したロジック。
    - 夜間バッチ更新 job: J-Quants から差分取得して `market_calendar` を冪等更新する `calendar_update_job` を実装（バックフィル・健全性チェックあり）。
  - ETL パイプライン（pipeline / etl）
    - ETL の実行結果を格納する `ETLResult` データクラスを公開（target 日付、取得件数、保存件数、品質問題リスト、エラーリスト等）。
    - 差分取得、バックフィル、品質チェックの実装方針を反映（J-Quants クライアント経由で idempotent に保存）。
    - DuckDB の実装差異（executemany に空リストを渡せない）を踏まえた安全な DB 書き込みロジックを採用。

- 研究・リサーチ機能（kabusys.research）
  - factor_research
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - ボラティリティ / 流動性（calc_volatility）: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー（calc_value）: raw_financials と株価を組み合わせて PER / ROE を算出（EPS 不在時は None）。
    - 実装は DuckDB 上の SQL を主体とし、結果は (date, code) をキーにした dict のリストで返却。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）の将来終値リターンを一括取得。
    - IC 計算（calc_ic）: ファクターと将来リターンのスピアマンランク相関を計算（必要最小レコード数チェックあり）。
    - 基本統計サマリー（factor_summary）・ランク化ユーティリティ（rank）を実装。
    - 外部依存（pandas 等）を使わず標準ライブラリで実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news と news_symbols を用いて、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - 処理の特徴:
      - JST ベースのニュースウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用）。
      - 1 銘柄あたり最大記事数 / 最大文字数でトリム（デフォルト: 10 件 / 3000 文字）。
      - バッチ処理（最大 20 銘柄／リクエスト）、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
      - レスポンスの厳格なバリデーション（JSON 抽出、results キー、code 一致、数値チェック）と ±1.0 にクリップして `ai_scores` テーブルへ書き込み（部分失敗時に既存スコアを保護する設計）。
      - テスト用フック: OpenAI 呼び出し関数（_call_openai_api）をモンキーパッチ可能。
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し `market_regime` テーブルへ冪等書き込み。
    - 処理の特徴:
      - ma200_ratio 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを回避。
      - マクロニュースは news_nlp のウィンドウ関数を利用し、OpenAI（gpt-4o-mini）で JSON 応答を期待。
      - API エラーやパース失敗時はフェイルセーフとして macro_sentiment=0.0 を使用し継続。
      - 再試行・バックオフロジックを実装（最大リトライ回数等）。
      - OpenAI 呼び出しのテスト差し替えが可能（内部の _call_openai_api は別実装でモジュール結合を抑制）。

### Design / Implementation Notes
- ルックアヘッドバイアス回避
  - 主要なスコアリング関数（score_news, score_regime, calc_* 関数等）は内部で datetime.today()/date.today() を参照せず、引数の target_date に基づいて計算を行うよう設計。
- DB 書き込みは冪等性優先
  - market_regime / ai_scores / market_calendar 等の書き込みは DELETE→INSERT もしくは ON CONFLICT 方針等で冪等性を担保。トランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を保つ。
- エラー処理とフォールバック
  - OpenAI API 呼び出しや外部 API の一時的失敗はリトライとゼロフォールバック（例: macro_sentiment=0.0）によりサービス全体の頑健性を確保。
  - データ不足（例: MA200 のデータ不足）は中立値（1.0 等）で処理を継続しログ出力。
- DuckDB 互換性への配慮
  - DuckDB の実装差異（executemany に空リスト不可 など）を考慮して、条件付きで executemany を呼ぶ実装になっている。
- テスト容易性
  - OpenAI 呼び出し箇所は内部で関数を経由し、unittest.mock などで差し替え可能にしている。
- 環境変数 / .env パースの挙動
  - export プレフィックスやシングル/ダブルクォート内のバックスラッシュエスケープ、行末コメントの処理など、一般的な .env の記法に対応。
  - .env 読み込み失敗は警告ログ出力で安全に無視。

### Security
- 本バージョンには特記すべきセキュリティ修正はありません。  
- 機密 API トークン（OpenAI, J-Quants, kabu API 等）は環境変数経由で提供する設計。`.env` ファイルをコミットしない運用を推奨。

### Known limitations / TODO
- 一部モジュール（strategy, execution, monitoring）の具体的な実装はパッケージエクスポートに含まれているが、当バージョンでの詳細実装は限定的な可能性あり（将来的に追加・拡張予定）。
- OpenAI レスポンスの厳密なフォーマット依存があるため、モデルや API の進化によりプロンプト・レスポンスパース部の調整が必要となる可能性がある。
- DuckDB バインドの詳細（配列バインド等）は DB バージョン依存のため、運用環境での検証を推奨。

---

今後のリリースでは、ユーザーからのフィードバックに基づくバグ修正、性能改善、戦略・発注周りの実装追加を予定しています。