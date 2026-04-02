Keep a Changelog
=================

すべての変更はセマンティック バージョニングに従います。  
このファイルは Keep a Changelog の形式に準拠して記載しています。

Unreleased
---------

(現在、未リリースの変更はありません)

0.1.0 - 2026-04-02
-----------------

Added
- パッケージ初期リリース。
- 基本モジュール群を追加:
  - kabusys.config
    - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - 高度な .env パーサを実装（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理等）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト用）。
    - 環境設定を扱う Settings クラスを導入（J-Quants / kabu ステーション / Slack / DB / 監視 / システム設定をプロパティで取得）。
    - 環境変数検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須変数未設定時の例外処理を実装。
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価する score_news を実装。
    - バッチ処理（最大20銘柄/リクエスト）、記事/文字数トリム、JSON Mode 応答のバリデーションをサポート。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、フェイルセーフ（失敗時はそのチャンクをスキップ）を実装。
    - レスポンス検証ロジック（results キー, code の一致, スコア数値・有限性チェック）と ±1.0 のクリップ処理を実装。
    - テスト容易性のため OpenAI API 呼び出し箇所を差し替え可能（unittest.mock.patch で置換可能）。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム判定（bull/neutral/bear）を行う score_regime を実装。
    - MA 計算はルックアヘッドバイアス防止のため target_date 未満のデータのみを使用。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - レジーム結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - kabusys.data
    - calendar_management
      - JPX マーケットカレンダーの管理と夜間バッチ更新（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 保存（冪等）。
      - 営業日判定用ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB データがない場合は曜日（平日）ベースのフォールバックを行う設計。
      - 最大探索範囲やバックフィル、健全性チェックを実装して異常データを保護。
    - pipeline / etl
      - ETLResult データクラスおよび ETL パイプライン用ユーティリティを追加。差分取得・保存・品質チェックの設計に対応。
      - ETLResult に品質問題とエラーの集約、辞書変換ユーティリティを実装。
      - DuckDB を用いたテーブル存在チェックや最大日付取得等の内部ユーティリティを実装。
  - kabusys.research
    - factor_research
      - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
      - DuckDB SQL を活用して営業日ベースの窓集計を行い、データ不足時は None を返す設計。
    - feature_exploration
      - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を提供。
      - 外部依存を避け、純粋に標準ライブラリと DuckDB で実装。
  - パッケージ初期構成ファイル:
    - kabusys.__init__ に __version__ = "0.1.0" を設定。
    - モジュールの __all__ エクスポートを整備。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （現時点での既知のセキュリティ修正はなし）

Notes / 設計上の重要点
- ルックアヘッドバイアス対策:
  - AI バッチ（news_nlp, regime_detector）やファクター計算は internal において datetime.today()/date.today() を直接参照せず、必ず caller が target_date を渡す設計。
  - DB クエリは target_date 未満/以上の排他条件を明示して将来データ参照を防止。
- 耐障害性:
  - OpenAI API 呼び出しはリトライ/バックオフ処理を実装し、致命的失敗時でもプロセス全体が停止しないようフェイルセーフ（スコアは 0.0 にフォールバック、該当チャンクはスキップ）を採用。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 方針の想定）して実装。
- テスト性:
  - OpenAI 呼び出し箇所はモジュール内プライベート関数をモック可能（ユニットテストで差し替えやすい）。

互換性 / 破壊的変更
- 初期リリースのため破壊的変更はなし。今後のリリースでは設定キー名や DB スキーマに影響する変更が発生する可能性があります。変更時はセマンティックバージョニングと本 CHANGELOG にて明示します。

貢献
- 初期実装に対するバグ報告や改善提案は issue を作成してください。テスト可能な差分はプルリクエスト歓迎します。