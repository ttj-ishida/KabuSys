# CHANGELOG

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新更新: 2026-04-01

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-01

初回リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装・公開します。
主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パブリック API として data, strategy, execution, monitoring を公開（__all__）。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（カレントワーキングディレクトリに依存しない設計）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。`.env.local` は上書きが可能。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用）。
  - .env パーサ:
    - `export KEY=val` 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート外は空白直前の `#` をコメントとみなす）などに対応。
  - Settings クラスに各種設定プロパティを提供（J-Quants, kabuステーション API, Slack, DB パス, 監視しきい値, 環境/ログレベル検証など）。
    - 必須環境変数未設定時は ValueError を送出して明示的にエラーを通知する。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL）を実装。
    - DB パスなどは Path オブジェクトとして返却。

- AI（自然言語処理）モジュール
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を集約して銘柄別にニューステキストを構築し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメントを算出。
    - チャンク処理（1回最大 20 銘柄）、1銘柄あたりの最大記事数/文字数でトリム、レスポンスの厳密なバリデーションを実装。
    - リトライポリシー：429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ、その他はスキップ。API 失敗時はそのチャンクをスキップして処理継続（フェイルセーフ）。
    - レスポンスパース時の耐障害性（JSON 前後ノイズからの復元）とスコアの ±1.0 クリップ。
    - テスト容易性考慮：OpenAI 呼び出し部は差し替え可能（_call_openai_api を patch 可能）。
    - 出力を ai_scores テーブルへ冪等的に書き込み（対象コードのみ DELETE → INSERT）。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースは `news_nlp.calc_news_window` を用いる時間ウィンドウで取得し、OpenAI（gpt-4o-mini）へ送信。
    - API 呼び出しに対するリトライ・バックオフ、API 失敗時の macro_sentiment=0.0 フェイルセーフ、結果のクリップと閾値評価を実装。
    - 判定結果は market_regime テーブルへトランザクションで冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- リサーチ（ファクター・特徴量探索）モジュール (`kabusys.research`)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（ma200_dev）を prices_daily から算出。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を算出（true range の NULL 伝播を適切に扱う）。
    - calc_value: raw_financials から直近財務データを取得し PER, ROE を計算（EPS が 0/欠損時は None）。
    - SQL と窓関数を活用した DuckDB ベースの実装で、外部 API にはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 件未満は None）。
    - rank: 平均ランク（同順位は平均ランク）を計算（丸めで ties 検出を安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - すべての関数は lookahead（ルックアヘッド）バイアスを防ぐために日時 API（datetime.today()/date.today()）に依存しない実装。

- データプラットフォーム・ETL (`kabusys.data`)
  - calendar_management:
    - market_calendar を利用した営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日を休場）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に保存。バックフィル・健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得件数・保存件数・品質チェック結果・エラー一覧等を含む）。
    - ETL パイプライン方針の骨子（差分更新、保存は idempotent、品質チェックは収集して継続）を実装方針として反映。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- ロギング・耐障害設計
  - 各モジュールで詳細な logger 呼び出しを配置し、警告・情報・デバッグログで状態把握が可能。
  - 外部 API 依存部分は失敗時フォールバック（例: macro_sentiment=0.0、部分チャンクスキップ）を採用しシステムの継続性を重視。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / 既知の問題 (Known issues / Notes)
- ETL pipeline 内の関数実装の一部でソースが途切れている箇所が見受けられます（pipeline._get_max_date の末尾に `return date.fro` のような不完全な記述があり、これは実行時エラーとなる可能性があります）。リリース後に修正予定。
- パッケージの __all__ に strategy, execution, monitoring が含まれるが、今回提示されたコードにはそれらの実装ファイルが含まれていません。これらは別途実装または追加リリースで提供される想定です。
- OpenAI API 利用には有効な OPENAI_API_KEY が必要。API 呼び出し時のモデルは gpt-4o-mini を指定（変更の可能性あり）。
- DuckDB のバージョン差異に依存するバインド挙動（executemany 空リスト不可等）に対する対処がコードに含まれています。運用環境の DuckDB バージョンでの動作確認を推奨。

### 実装方針（ドキュメント的備考）
- ルックアヘッドバイアス防止: 日付計算はすべて外部から与えられる target_date に基づき、内部で date.today()/datetime.today() を参照しない設計。
- テスト容易性: OpenAI 呼び出し部分はモック差し替え可能に実装されておりユニットテストの容易化を意図。
- データベース書き込み: 重要な書き込みはトランザクションで冪等性を確保（DELETE → INSERT）し、部分失敗時に既存データを保護する設計。

---

今後のリリース予定（例）
- strategy / execution / monitoring モジュールの実装追加（実取引ロジックと監視エージェント）。
- ETL pipeline の残実装およびテスト整備、ドキュメント拡充。
- OpenAI 呼び出しのプラガブル化（バックエンド選択肢、コスト制御等）。
- 単体テスト・統合テストの追加と CI 設定。

--- 

（注）この CHANGELOG は提示されたソースコードから推測して作成したものであり、実際のコミット履歴とは異なる可能性があります。必要に応じて実際の変更点に合わせて調整してください。