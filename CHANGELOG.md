# Keep a Changelog — CHANGELOG.md（推定・コードベースから作成）

注: 以下は提示されたコードスナップショットの内容から変更点・機能を推測して作成した変更履歴です。実際のコミット履歴に基づくものではありません。

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-31

Added
- パッケージ初期導入: kabusys パッケージの基本構成を追加
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0"、公開サブパッケージ一覧を定義。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定をロードする自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml）。
    - .env パース実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント扱いを考慮した堅牢なパーサーを実装。
    - .env の読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - 必須環境変数チェック用 _require() と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / ログレベル / 実行環境フラグ等）。
    - 環境値の妥当性検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）と便利な is_live / is_paper / is_dev プロパティを追加。
- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを算出し、ai_scores テーブルに保存する処理を実装。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、内部は UTC naive datetime）。
    - バッチ処理（最大 20 銘柄／リクエスト）、1銘柄あたり記事トリム（記事数・文字数上限）を実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code/score チェック、数値変換、スコアクリッピング）。
    - エラー耐性設計: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、非リトライエラーはスキップし処理継続（フェイルセーフ）。
    - DuckDB 互換性配慮（executemany に空リストを渡さない等）。
  - src/kabusys/ai/regime_detector.py
    - ETF（1321）200日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し、market_regime テーブルに冪等書き込み。
    - prices_daily 参照におけるルックアヘッド防止（target_date 未満データのみ使用）。
    - LLM 呼び出しは失敗時に macro_sentiment = 0.0 で継続（フォールバック）。OpenAI 呼び出し用の独立した内部実装（モジュール結合低減）。
    - リトライロジック（RateLimit, APIConnection, Timeout, APIError の 5xx 扱い）と指数バックオフを実装。
- データプラットフォーム・ユーティリティ
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジックを実装: market_calendar を用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間バッチ更新（calendar_update_job）。
    - DB が欠落している場合の曜日ベースフォールバック、最大探索日数制限、バックフィル/健全性チェックを実装。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL の公開インターフェースと ETLResult データクラスを実装（取得数・保存数・品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェックの設計方針（品質問題は収集して呼び出し元へ報告）を反映。
    - jquants_client を利用したデータ取得/保存の想定（詳細は jquants_client モジュールに依存）。
- リサーチ（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR, 相対 ATR）、Value（PER, ROE）などのファクター計算関数を実装。DuckDB 上の SQL ウィンドウ関数を活用。
    - データ不足時の None 扱い、返り値は date と code を含む dict リスト。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（fwd_1d, fwd_5d, fwd_21d 等）、IC（Spearman のスピアマンランク相関）計算、ファクター統計サマリー、ランク付けユーティリティを実装。
    - pandas 等に依存しない純 Python 実装、ties の平均ランク処理、入力検証を実施。
  - src/kabusys/research/__init__.py による主要関数の再エクスポートと公開。
- 内部ライブラリ設計上の共通ポリシー（ドキュメント化）
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を直接参照しない設計が明示されている関数群がある（テスト容易性と安全性を重視）。
  - DuckDB を主要な分析 DB として使用、SQL と Python の組合せで大量データ処理を行う実装方針。
  - 大域的な例外はキャッチしてログ出力のうえ部分的な処理継続（フェイルセーフ）とする設計。

Changed
- なし（初回リリースと推定）

Fixed
- なし（初回リリースと推定）

Removed
- なし（初回リリースと推定）

Security
- 環境変数の自動ロード時に OS 環境変数を保護するため protected set を導入（既存 OS 環境を上書きしない設計）。
- OpenAI API キーは引数で注入可能で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出することで明示的なエラー検出を行う。

Notes / 注意点（コードから推測）
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を利用する実装であり、レスポンスのパースやエラー処理に細心の注意が払われている（JSON前後ノイズの復元処理等）。
- DuckDB の executemany やリストバインドの互換性に配慮した実装がされている（空リスト回避）。
- 一部モジュール（jquants_client 等）は外部依存を想定しており、実稼働時は API クライアントや DB スキーマの準備が必要。
- 本CHANGELOGはコードベースの状態から推測して作成しており、実際のコミット履歴や変更日時とは異なる可能性があります。