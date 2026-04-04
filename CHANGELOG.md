CHANGELOG
=========
（このファイルは Keep a Changelog の形式に準拠しています）
すべての重要な変更をここに記載します。枠組み: Added / Changed / Fixed / Security / Notes

0.1.0 — 2026-04-04
------------------

Added
- パッケージの初期リリース: kabusys v0.1.0
  - パッケージトップ: src/kabusys/__init__.py にてバージョン管理と公開モジュールを定義。
- 環境・設定管理モジュール（src/kabusys/config.py）
  - .env および .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - export KEY=val 形式やクォート、インラインコメントなど一般的な .env 構文に対応するパーサを実装。
  - OS 環境変数を保護するための上書き制御（.env と .env.local の読み込み優先度を実装）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム設定等のプロパティで型付きアクセスを可能に。
  - 環境変数の必須チェックを行い、未設定時は明確なエラーを送出するユーティリティを実装。
- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとの ai_score を算出し ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）の計算、記事数/文字数制限、チャンクバッチ（最大20銘柄）処理、レスポンス検証、スコアのクリップなどを実装。
    - 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフ・リトライ実装と、失敗時のフェイルセーフ（スキップ）を導入。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api の patch を想定）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースによる LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。API失敗時はマクロセンチメントを 0 にフォールバックするフェイルセーフを導入。
    - ルックアヘッドバイアス防止のため、target_date 未満データのみを参照する実装。
- Research モジュール（src/kabusys/research）
  - factor_research: モメンタム（1M/3M/6M と MA200 乖離）、ボラティリティ（20日 ATR / 相対ATR / 平均売買代金 / 出来高比率）、バリュー（PER, ROE）を DuckDB 上で計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ファクターの統計サマリー（factor_summary）やランク変換（rank）を実装。外部依存を持たず標準ライブラリのみで実装。
  - zscore_normalize を含むデータ統計ユーティリティを再エクスポート。
- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの取得/更新、営業日判定(is_trading_day)、翌営業日/前営業日、期間内営業日列挙、SQ判定、夜間バッチ更新ジョブ(calendar_update_job) を実装。
    - DB データが存在しない場合は曜日ベースのフォールバックを行う等、一貫したフォールバックロジックを導入。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - 差分取得、idempotent 保存、品質チェックのための ETLResult データクラスを提供。
    - backfill_days・calendar lookahead 等の制御を備え、品質チェックの問題は収集して呼び出し元で処理可能にする設計。
  - jquants_client と quality モジュールとの連携を想定したインターフェースを整備。
- research/__init__.py と ai/__init__.py 等で公開 API を明示的に定義。

Changed
- 設計上の方針・実装の注意点（ドキュメント化）
  - 主要な AI / ETL / Research 関数はルックアヘッドバイアスを避けるため datetime.today() / date.today() を内部で参照しない（引数で target_date を必須にする）。
  - DuckDB の互換性を考慮し、executemany に空リストを渡さない等の実装上のワークアラウンドを適用。
  - OpenAI のレスポンスパースで JSON mode でも前後ノイズが入る可能性を考慮し、最外の {} を抽出する復元ロジックを導入。
  - API 呼び出し失敗時は「例外を上位へ伝播させず継続」する挙動（フェイルセーフ）を多くの処理で採用。DB 書き込み時のみ例外を伝播しトランザクションでロールバックする設計。
  - market_regime / ai_scores 等テーブルへの書き込みは冪等性を確保（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK）する方式を採用。
  - .env パーサと自動ロードはワークフロー（テスト環境含む）を考慮し保護キーや override の挙動を明確化。

Fixed
- なし（初期リリースのため変更履歴は追加中心）

Security
- 環境変数の取り扱い
  - OS 環境変数をプロテクトするため .env の上書きルールを実装（読み込み時 protected set を作成）。
  - OpenAI API キーが未設定の場合は ValueError を送出して明確に失敗させる（score_news / score_regime）。ただし API レスポンス失敗はフェイルセーフでスコアを 0 またはスキップする挙動を採用。
- .env 自動読み込みはオプトアウト可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / テスト用フック
- OpenAI 呼び出しを行う内部関数（_call_openai_api）が各モジュールで定義されており、unittest.mock.patch による差し替えを想定している（テスト容易性）。
- DuckDB を前提とした実装であり、日付型の変換ユーティリティ（_to_date）やテーブル存在チェックなどのユーティリティを用意。
- ロギングを多用しており、実行状況やフェイルオーバーのトレースが容易。
- デフォルト値や閾値（MA window, ATR window, バッチサイズ, リトライ回数など）はソースコード内の定数として明示されているため、必要に応じてチューニング可能。

今後の予定（推測）
- モニタリング / 実行（execution / monitoring）関連の実装追加、運用向け CLI やデーモン化、アラート配信（LINE 連携の活用）など。
- テストカバレッジ拡充と CI パイプライン整備。
- jquants_client / kabu ステーション等外部クライアント実装の提供・安定化。

お問い合わせ
- 実装上の不明点や挙動確認が必要であれば、該当モジュール名（ファイルパス）を指定して質問してください。コード内の docstring・ログメッセージを参照してより詳細な変更説明を作成します。