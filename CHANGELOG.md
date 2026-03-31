Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の規約に沿ってバージョン管理しています。

フォーマット: YYYY-MM-DD

0.1.0 - 2026-03-31
------------------

Added
- 初期リリース。日本株自動売買システムのコアライブラリを導入。
- パッケージエントリポイント
  - kabusys パッケージ（__version__ = 0.1.0）と公開サブパッケージ: data, strategy, execution, monitoring を定義。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数を自動読み込み（プロジェクトルート探索: .git または pyproject.toml）。
  - .env/.env.local の優先順設定と .env.local による上書きサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - export KEY=val 形式やシングル/ダブルクォート、エスケープ、コメント行対応の柔軟な .env パーサ実装。
  - 環境変数保護（OS 環境変数を protected として上書き防止）。
  - Settings クラスで主要設定をプロパティとして公開（J-Quants / kabuステーション / Slack / DB パス / 環境 / ログレベル判定など）。不正値チェック（有効な env / log level の検証）を実装。
  - 必須変数未設定時に ValueError を送出する _require ヘルパー。

- データ関連（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が未取得のときは曜日ベースでフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル・健全性チェック・冪等保存（ON CONFLICT 仕様を想定）を実装。
  - pipeline / etl: ETL 用のインターフェースと ETLResult データクラスを提供。
    - ETLResult は取得件数／保存件数／品質問題／エラーを集約し、辞書変換メソッドを持つ。
    - 差分取得用のユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
  - ETL の設計指針: 差分更新・バックフィル・品質チェックの収集・idempotent 保存を想定。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（ai_score）を算出し ai_scores に保存するフローを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と UTC での比較処理を実装する calc_news_window。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの最大記事数・最大文字数トリム、JSON mode のレスポンス検証とスコアクリップ（±1.0）。
    - OpenAI エラー（429、タイムアウト、ネットワーク断、5xx）に対するエクスポネンシャルバックオフのリトライ実装。
    - レスポンスの復元ロジック（JSON 前後ノイズから最外の {} を抽出）や不正レスポンスのロギングとスキップ（例外を上げず継続）。
    - テスト容易性のため _call_openai_api が patch 可能な設計。
  - regime_detector:
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う score_regime を実装。
    - マクロ記事抽出、OpenAI 呼び出し、retry/backoff、API失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため date.today() を参照せず、prices_daily クエリに date < target_date の排他条件を採用。
    - OpenAI 呼び出しは独立実装（news_nlp とは共有しない）でモジュール間結合を低減。
    - レスポンス JSON パースや API エラーに耐える堅牢化。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび MA200 乖離率を計算。データ不足時の None ハンドリング。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range 計算における NULL 伝播制御。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS が 0 または欠損のとき None）。
    - 設計方針: DuckDB の SQL を利用し prices_daily / raw_financials のみ参照、本番発注 API へはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーション実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。データ不足時は None。
    - rank: 同順位は平均ランクを返すランク変換ユーティリティ。
    - factor_summary: 各ファクターカラムの count/mean/std/min/max/median を計算する統計サマリ機能。
    - pandas 等外部ライブラリに依存しない純 Python 実装を採用。

Changed
- 多数のモジュールで「ルックアヘッドバイアス防止」を明示的に設計方針として採用（日付参照を関数引数に限定、内部での今日参照を排除）。
- OpenAI API 呼び出し周りを堅牢化（リトライ・バックオフ・JSON 復元・fail-safe フォールバック）し、外部 API の不安定性に対して処理継続を優先する方針を反映。
- DuckDB への書き込みで部分失敗時に既存データを保護するため、対象コードを絞って DELETE → INSERT する戦略を採用（ai_scores の部分置換など）。
- .env パーサの挙動を改善し、export プレフィックス・クォート内エスケープ・コメント判別を強化。

Fixed
- news_nlp / regime_detector における OpenAI レスポンスのパース失敗時に処理がクラッシュする問題を防止（警告ログを出しスキップまたはデフォルト値で継続）。
- DuckDB の executemany に空リストを渡すと失敗する点を回避するため、空リストチェックを追加。
- calendar_update_job の健全性チェックを追加し、極端に未来の last_date を検出した場合に誤った更新を防止。

Security
- 特になし（このバージョンでのセキュリティ修正はありません）。環境変数や API キーは Settings 経由で扱い、直接ログに出力しない方針。

Deprecated
- なし

Removed
- なし

Notes / 開発上の重要なポイント
- テスト容易性を考慮し、OpenAI への呼び出し箇所は内部関数をパッチ可能にしている（unittest.mock.patch を想定）。
- 日付・時刻の扱いは全て timezone-naive な datetime/date を利用し、JST ↔ UTC の変換を明確に実装（ニュースウィンドウなど）。
- ETL やカレンダー更新は冪等性を重視（DB 側での上書き想定・部分書き換えによる既存データ保護）。
- 将来的な変更（モデル名・API仕様・DB スキーマ変更等）を見越し、エラーはログに残して処理を続ける安全設計を優先。

今後の予定（想定）
- strategy / execution / monitoring サブパッケージの実装・統合テストの追加。
- テスト用モックや CI ワークフローの整備（OpenAI / J-Quants クライアントのエミュレーション）。
- パフォーマンス最適化（大規模データ処理時の DuckDB クエリ最適化、バッチサイズ調整など）。

もし、より詳細な変更点や個別ファイルごとの差分（コミット単位のCHANGELOG）が必要であれば、提示してください。コード履歴（git log）があれば、さらに精密な CHANGELOG を生成できます。