CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に準拠しています。
リリース履歴は後方互換性・重要な設計判断・フェイルセーフ動作を分かりやすく示すように記述しています。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

[Unreleased]
-----------
（現時点のコードベースは初回公開と推測されるため、主要な変更は v0.1.0 に記載しています。以降の変更はここに追記してください。）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。

- 設定・環境変数管理モジュール
  - src/kabusys/config.py
    - .env / .env.local 自動ロード機能を実装（プロジェクトルートの検出は .git / pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化が可能。
    - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応。
    - 環境変数の上書き制御（override）と保護セット（protected）をサポート。
    - Settings クラスを追加し、J-Quants トークンや kabuAPI のパス、DB パス、監視閾値、ログレベル、環境（development/paper_trading/live）などの読み取り用プロパティを提供。
    - 必須環境変数未設定時は _require が ValueError を送出し明示的に失敗する設計。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄別に集約し、OpenAI（gpt-4o-mini, JSON Mode）を用いてセンチメントを -1.0〜1.0 で評価。
    - タイムウィンドウは JST 前日 15:00 ～ 当日 08:30（UTC に変換）で算出する calc_news_window を実装。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、1銘柄あたりの記事数・文字数上限（トリム）を持つ。
    - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスのバリデーション（JSON 抽出、results リスト、code の検証、数値スコアの検査）を行い、部分失敗があっても他銘柄のスコアを保持する安全な DB 書き込み（DELETE → INSERT）を行う。
    - テスト容易性のため _call_openai_api を patch できる設計。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードフィルタリングを行い、LLM 呼び出し失敗時は macro_sentiment = 0.0 にフォールバック。
    - OpenAI 呼び出し（gpt-4o-mini）を独立実装し、news_nlp モジュールとは共有しないことでモジュール結合を低減。
    - スコア合成後は market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試みて例外を再送出。

- リサーチ / ファクター計算
  - src/kabusys/research/*
    - factor_research.py: Momentum（1M/3M/6M、MA200乖離）、Value（PER/ROE）、Volatility（20日ATR）、Liquidity（20日平均売買代金／出来高比）等のファクター計算を実装。DuckDB 内の prices_daily / raw_financials のみ参照。
    - feature_exploration.py: 将来リターン calc_forward_returns、IC（Spearman）計算 calc_ic、ランク変換 rank、ファクター統計 summary（factor_summary）を実装。外部ライブラリに依存せず純粋 Python + SQL で実装。
    - research パッケージの __init__ で主要 API をエクスポート。

- データプラットフォーム / ETL
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理 API 統合（J-Quants 経由）を想定した夜間バッチ更新（calendar_update_job）を実装。
    - 営業日判定、next/prev_trading_day、get_trading_days、is_sq_day の一貫した振る舞いを提供。market_calendar が未取得のときは曜日ベースでフォールバック。
    - DB に登録されている日付を優先し、未登録日は曜日フォールバックで補う。探索の最大日数制限を実装して無限ループ防止。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプラインの骨格を実装。差分取得、保存、品質チェックフローを想定。
    - ETLResult dataclass を提供（target_date、取得/保存件数、品質問題リスト、エラーリストなどを保持）。to_dict により監査ログ向けに変換可能。
    - jquants_client（外部モジュール想定）経由で保存処理を呼び出す設計。品質チェックモジュールと連携するインターフェースを想定。
    - デフォルトでバックフィルやカレンダー先読みを行う挙動を盛り込む。

Changed
- 設計方針・フェイルセーフの明確化（ライブラリ全体）
  - 時刻に関するルックアヘッドバイアスを避けるため、datetime.today()/date.today() を参照しない実装（ほとんどのコア処理が target_date 引数を受け取る）。
  - LLM 呼び出しの失敗に対しては例外で停止させず、フェイルセーフな既定値を用いる（ニュース系: スコア取得失敗時は 0.0、ETL は品質問題を収集して処理継続など）。

Fixed
- DB 書き込みの冪等性と部分失敗時の保護
  - ai_scores / market_regime への書き込みは、該当コード/日付のみを削除してから挿入する手順を採用。DuckDB の executemany における空リストの制約を回避するチェックを導入。

Security
- 環境変数の取り扱いに注意
  - 自動ロード時に既存の OS 環境変数は protected として上書きされない（.env の override の取り扱いを明示）。
  - OpenAI API キーが未設定の場合、news_nlp.score_news および regime_detector.score_regime は ValueError を送出して明示的に失敗させる（誤った無鍵呼び出しを防止）。

Notes / 既知の挙動
- OpenAI API 呼び出しは gpt-4o-mini + JSON Mode を利用する前提で実装されている。API レスポンスは厳密な JSON を期待するが、JSON 前後に余計なテキストが混入するケースに備えた復元ロジックを持つ。
- news_nlp/regime_detector の内部で使用する _call_openai_api はテスト時に patch できるようになっている（ユニットテストで外部 API を差し替え可能）。
- 一部の関数（calendar_update_job や ETL の一部）は jquants_client 等外部モジュールに依存しており、実行にはそれらの実装またはモックが必要。
- date / datetime の扱いはすべて timezone-agnostic（UTC naive で統一）に設計されているため、外部との時刻連携時は注意が必要。

今後
- README / ドキュメントに具体的な初期セットアップ手順（.env.example、J-Quants / OpenAI の設定方法、DuckDB スキーマ）を追加予定。
- テストカバレッジを拡張し、外部 API 呼び出しのモックを用いた統合テストを整備予定。
- ai_scores に対する評価指標（confidence 等）や、レジーム判定の閾値チューニング UI を検討中。

以上。必要であれば特定モジュールごとの詳細な変更点（例: 関数シグネチャ、戻り値の例、サンプル SQL）を追記します。どのレベルの詳細が必要か教えてください。