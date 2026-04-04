CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
変更内容はコードベースの実装内容から推測して記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)。
- 基本モジュール群を実装：
  - kabusys.config
    - .env ファイルと環境変数から設定を自動読込する仕組みを追加（プロジェクトルート検出：.git または pyproject.toml）。
    - .env / .env.local の優先順位をサポート（.env.local が上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止オプション。
    - .env 行パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォートとエスケープ処理、インラインコメントの扱い等に対応）。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム環境をプロパティ経由で取得可能に。
    - 必須環境変数未設定時には明示的なエラーを投げる _require 実装。
  - kabusys.data
    - calendar_management: JPX マーケットカレンダー管理、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）と夜間更新ジョブ (calendar_update_job) を実装。DB 未取得時の曜日ベースフォールバックや健全性チェック、バックフィルロジックを備える。
    - pipeline / etl: ETLResult データクラスを含む ETL パイプライン補助（差分取得、バックフィル、品質チェックの設計方針記載）。
    - etl.py で ETLResult を再エクスポート。
  - kabusys.ai
    - news_nlp: ニュース記事を銘柄別に集約して OpenAI（gpt-4o-mini）の JSON mode を使いセンチメントスコアを計算し ai_scores に書き込む実装（time window 計算、チャンク処理、バッチサイズ、トリム、レスポンス検証、クリッピング、部分置換による冪等書き込み）。
    - regime_detector: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime に日次で判定・保存する機能（API 再試行、フェイルセーフ、冪等 DB 書き込み）。
  - kabusys.research
    - factor_research: Momentum / Volatility / Value 等の定量ファクター計算（prices_daily / raw_financials を参照）。MA200 乖離・ATR・平均売買代金等を計算。
    - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク変換ユーティリティを実装。
  - パッケージ初期化で __version__ = "0.1.0" を設定。

Changed
- 初期実装だが、各モジュールで「ルックアヘッドバイアス」回避の設計を徹底（datetime.today()/date.today() を直接参照しない、クエリで date < target_date 等の排他条件を採用）。
- DuckDB の互換性を考慮した実装（executemany に空リストを渡さないガード、日付値の型変換ユーティリティ _to_date を提供）。
- OpenAI 呼び出しはモジュール単位でプライベート実装を分離（テストで差し替え可能に設計）。

Fixed / Robustness
- OpenAI API 呼び出しで発生し得るエラー（429 / 接続断 / タイムアウト / 5xx）に対して指数バックオフとリトライ処理を実装。最大試行回数や待機時間は定数で管理。
- OpenAI レスポンスの JSON パースで余計な前後テキストが混入するケースに対して最外の {} 抽出を試みるフォールバック実装。
- API 呼び出し失敗時は例外を上位に投げずフェイルセーフにフォールバック（マクロセンチメントや銘柄スコアは 0.0 またはスキップして処理継続）。ただし必須の API キー未設定時は ValueError を投げる。
- DB 書き込みは冪等処理とトランザクション（BEGIN / DELETE / INSERT / COMMIT）を採用し、失敗時は ROLLBACK を行い失敗を上位に伝播。ROLLBACK 自体が失敗した場合は警告ログを出力。
- raw_news の銘柄別テキストをトリムしてプロンプト過大を防止（1銘柄あたりの文字数上限）。
- スコアは ±1.0 にクリップして異常値を防止。
- 各計算関数はデータ不足時の挙動を明確化（例：ma200 データ不足で中立値返却、ATR 未満行数で None 等）。

Security
- 環境変数の自動ロード時に既存 OS 環境変数を保護する仕組みを導入（protected set）。.env 読み込み失敗時は警告ログを出す。
- KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 env ロードの無効化オプションを提供（テスト用途を想定）。

Notes / Implementation details
- news_nlp と regime_detector は OpenAI JSON mode（厳密な JSON 出力を期待）を利用するが、レスポンスの堅牢性対策として複数の検証ステップ・フォールバックを実装している。
- calendar_update_job は J-Quants クライアントを利用して差分取得 → save_* 系で ON CONFLICT 更新を想定している（外部 jquants_client 実装に依存）。
- research モジュールは外部ライブラリ（pandas 等）に依存せず、標準ライブラリ + DuckDB SQL で計算を行う設計。

Deprecated
- なし

Removed
- なし

Security
- なし（既知の脆弱性無し・環境変数/キー管理に関する運用上の注意を README 等で併記推奨）

今後の検討項目（コードからの示唆）
- OpenAI のレスポンス検証をさらに厳格化する（スキーマ検証ライブラリ導入の検討）。
- ETL の品質チェックで検出された問題の扱い（自動通知や再処理ワークフロー）を強化。
- 単体テスト / CI で OpenAI 呼び出しや DuckDB トランザクションのモックを整備。