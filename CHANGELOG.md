CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に従います。  
フォーマットのポリシー: 変更は「Added / Changed / Fixed / Removed / Deprecated / Security」のセクションに分類します。

Unreleased
----------

（次回リリースに向けた保持領域）

0.1.0 - 2026-03-29
-----------------

Added
- 初期リリース: KabuSys 日本株自動売買システムのコア機能を追加。
- パッケージ公開
  - パッケージ情報: src/kabusys/__init__.py にて __version__ = "0.1.0"、主要サブパッケージを __all__ で公開。
- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルートを .git / pyproject.toml で検出）を追加。
  - 優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env 行パーサーの実装（コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ対応）。
  - 必須変数チェック用の _require 関数、各種プロパティ（J-Quants、kabu API、Slack、DB パス、環境種別、ログレベル等）。
  - env 値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP (news_nlp.py)
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_score）を評価。
    - チャンク処理（1回の API 呼び出しで最大 20 銘柄）・記事数/文字数のトリム (_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK)。
    - JSON mode を前提としたレスポンスバリデーション、部分失敗に配慮した DB 書き込み（対象コードのみ DELETE → INSERT）。
    - リトライ/バックオフ（429・ネット障害・タイムアウト・5xx を対象）とフェイルセーフ（失敗時はスキップして継続）。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - calc_news_window(target_date) により JST ウィンドウを UTC naive datetime に変換（前日15:00〜当日08:30 JST 相当）。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出（マクロキーワード）→ OpenAI で -1.0〜1.0 の JSON 応答を期待 → スコア合成。
    - API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）、およびリトライポリシーを実装。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 1 を返す（成功時）。
- Data モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを元に営業日判定・前後営業日の検索・期間内営業日取得・SQ 判定等を提供。
    - DB 登録がない場合は曜日ベース（土日非営業）でフォールバック。DB 値が優先される一貫性のあるルール。
    - next_trading_day / prev_trading_day は最大探索日数制限を設けて安全（_MAX_SEARCH_DAYS）。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90) を実装し J-Quants からの差分取得と保存を行う（バックフィル・健全性チェックあり）。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを実装し、ETL の取得数・保存数・品質問題・エラー一覧を集約して返す。
    - 差分取得のためのユーティリティ（テーブル存在チェック、最大日付取得、バックフィル方針等）を実装。
    - データ品質チェックの結果を保持する設計（quality モジュールとの連携想定）。
    - etl.py で ETLResult を再エクスポート。
  - jquants クライアントとの連携ポイント（jquants_client を呼び出す設計箇所あり）。
- Research モジュール (src/kabusys/research)
  - factor_research.py
    - モメンタム、ボラティリティ（ATR, 平均売買代金等）、バリュー（PER/ROE）ファクター計算を実装。
    - DuckDB SQL を用いて prices_daily / raw_financials から計算。結果は (date, code) 辞書リストで返却。
    - 公開関数: calc_momentum, calc_volatility, calc_value。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、バリデーションあり）。
    - スピアマンのランク相関を用いた IC 計算 calc_ic。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計サマリー factor_summary。
    - research パッケージで主要関数を __all__ にて再公開。
- その他
  - モジュール間の依存を抑える設計（例: regime_detector と news_nlp は一部内部呼び出しを分離）。
  - OpenAI クライアント呼び出し箇所でテスト時に差し替えやすいように _call_openai_api をラップ。
  - DuckDB をデータ層のデフォルトとして想定した SQL 実装。

Changed
- n/a（初回リリースのため過去バージョンとの差分はなし）

Fixed
- n/a（初回リリース）

Removed
- n/a（初回リリース）

Deprecated
- n/a（初回リリース）

Security
- n/a（初回リリース）

Notes / 実装上の重要な挙動と設計判断
- ルックアヘッドバイアスの回避
  - score_news / score_regime 等の関数は内部で datetime.today() / date.today() を直接参照しない設計（target_date を必須引数とする）。
  - DB クエリは target_date 未満 / 排他条件を明確にして未来データを参照しない。
- フェイルセーフ設計
  - OpenAI API の失敗やパースエラーは致命的例外を投げずロギングしてフォールバック（例: macro_sentiment=0.0、スコア取得失敗時は当該チャンクをスキップ）。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 想定）。
- テストしやすさ
  - OpenAI 呼び出しや時間依存処理をモック/差し替えしやすいようラップを用意。
  - 環境変数自動ロードを無効化するフラグを用意（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- DuckDB 互換性
  - executemany に空リストを渡せない等の DuckDB の注意点に配慮した実装がある（空チェックを挟む等）。

既知の制約 / 今後の改善候補
- OpenAI の JSON Mode に依存したレスポンスパースは完全ではなく、外側の余計なテキスト混入時の復元ロジックを含むが、より堅牢なパースやスキーマ検証の追加を検討。
- 一部 SQL は DuckDB に依存した実装（ウィンドウ関数等）であり、別の DB に移行する場合は移植が必要。
- ETL の品質チェック結果をどのように運用フローに反映するか（自動停止かアラートのみか）を運用ルールとして明確化する必要あり。

---

ご要望があれば、各ファイル単位の変更ログ（より細かい実装ポイントや関数単位のリリースノート）を追加で生成します。