# CHANGELOG

このリポジトリの変更履歴は「Keep a Changelog」形式に従います。  
初回リリース（v0.1.0）はコードベースから推測して作成しています。

全般的な方針・注記
- ルックアヘッドバイアス回避のため、日付算出に datetime.today()/date.today() を直接参照しない設計が各モジュールで徹底されています（テスト容易性・再現性向上）。
- DuckDB を主要なローカルデータストアとして利用する設計になっています。多くの処理は SQL（DuckDB）で完結するよう実装されています。
- OpenAI（gpt-4o-mini）を JSON Mode で呼び出す実装があり、429/ネットワーク断/タイムアウト/5xx に対するリトライと指数バックオフを備えてフェイルセーフ化されています。
- テスト時の差し替えを想定したフック（例: _call_openai_api の patch）が用意されています。

Unreleased
- （なし）

[0.1.0] - 2026-03-29
Added
- 基本パッケージ構成
  - パッケージ識別子とバージョンを設定（kabusys.__version__ = "0.1.0"）。kabusys の主なサブパッケージ（data, research, ai, monitoring, strategy, execution 等）を __all__ で公開。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない自動 .env 読み込みを実装。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - OS 環境変数を保護する protected 機構と override 制御を実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須キー取得時の明示的エラー（_require）や、KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）を実装。
  - DuckDB/SQLite の既定パス設定（DUCKDB_PATH / SQLITE_PATH）を提供。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント（score_news）
    - raw_news と news_symbols を入力に、銘柄ごとのニュースを集約して OpenAI に投げ、ai_scores テーブルへ結果を書き込む処理を実装。
    - 1 銘柄あたり最大記事数・最大文字数でトリムするトークン増大対策（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - バッチ送信（最大 20 銘柄／API コール）、JSON mode のレスポンス検証、スコアクリップ（±1.0）、部分失敗に備えた部分的な DELETE→INSERT 書き換えロジックを実装。
    - calc_news_window(target_date) による JST ベースのニュースウィンドウ計算を提供（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う）。
    - API キー注入（引数または OPENAI_API_KEY 環境変数）、API リトライ/バックオフ、失敗時はスキップして継続するフェイルセーフ性。
  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定して market_regime テーブルに冪等書き込み。
    - マクロニュースは news_nlp.calc_news_window を利用して抽出し、OpenAI（gpt-4o-mini）へ投げて JSON パースで macro_sentiment を取得。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバックする安全化。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT のパターンで冪等性確保、失敗時は ROLLBACK し例外を伝播。

- ニュース NLP の実装詳細（src/kabusys/ai/news_nlp.py）
  - API 呼び出しの共通実装（_call_openai_api）とレスポンス検証（_validate_and_extract）を用意。
  - レスポンスの堅牢な JSON 復元（前後余計テキストを除去して {} を抽出）や型検証、未知コードフィルタリング、数値チェックを実装。
  - リトライ対象の例外種類（RateLimitError, APIConnectionError, APITimeoutError, 5xx）を明確化。

- データプラットフォーム／Research（src/kabusys/data, src/kabusys/research）
  - ETL パイプライン（pipeline.py）
    - ETLResult データクラスを実装し ETL 実行結果・品質問題・エラー集約をサポート。to_dict() により品質問題をシリアライズ可能。
    - 差分取得、バックフィル、品質チェックの設計方針を反映。
  - ETL インターフェースの再エクスポート（data/etl.py）。
  - マーケットカレンダー管理（data/calendar_management.py）
    - market_calendar テーブルに基づいた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job（J-Quants API からの差分取得と保存）を実装。
    - market_calendar が未取得の場合は曜日ベース（平日＝営業日）でフォールバックする一貫したロジック。
    - calendar_update_job はバックフィル、健全性チェック（将来日付の異常検出）や API 例外時のログ・スキップ処理を備える。
  - Research のファクター計算（research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER/ROE）を DuckDB の SQL を用いて計算する関数を提供。
    - データ不足時に None を返す安全化、結果を (date, code) ベースの辞書リストで返却。
  - 特徴量探索（research/feature_exploration.py）
    - 将来リターン算出（calc_forward_returns）、IC（calc_ic）計算（スピアマンのランク相関）、ランク変換ユーティリティ、ファクター統計サマリー（factor_summary）を実装。
    - horizons のバリデーション、重複除去、効率的な単一クエリ実行を行う実装。

- モジュールの再エクスポート
  - research パッケージ内で主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を __all__ で公開。
  - ai パッケージで score_news を __all__ で公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの注入は引数または環境変数（OPENAI_API_KEY）で行い、未設定時は明示的に ValueError を送出して誤使用を防止。
- .env 読み込みはプロジェクトルート検出に基づき自動で行われるが、明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Known limitations / Notes
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を前提としており、将来的なモデル/SDK 変更によっては適合処理の更新が必要になる可能性があります。
- DuckDB の executemany に空リストを渡せない制約を回避するため、空チェックを行ってから実行しています（互換性考慮）。
- 一部処理（calendar_update_job など）は J-Quants クライアント（kabusys.data.jquants_client）に依存しており、実行時に外部 API クレデンシャルとネットワークアクセスが必要です。
- 現フェーズでは PBR・配当利回り等のバリュー指標は未実装。

以上がこのコードベースから推測される初回リリース（v0.1.0）の変更点と主要実装内容です。必要であれば各セクションをファイル単位でさらに分解した詳しい変更点（例: 関数の挙動、戻り値の仕様、例外仕様）を追加します。どの程度の詳細が必要か教えてください。