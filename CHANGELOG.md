# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: [バージョン] - リリース日（YYYY-MM-DD）。カテゴリは Added / Changed / Fixed / Deprecated / Removed / Security。

### [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な機能は以下の通りです。

Added
- パッケージ基盤
  - src/kabusys/__init__.py: パッケージ初期化、バージョン "0.1.0"、主要サブパッケージを __all__ で公開。
- 環境設定管理
  - src/kabusys/config.py:
    - .env/.env.local 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）。
    - 高度な .env パーサ実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等）。
    - OS 環境変数を保護する protected オプション（.env.local は既存値を上書き可能だが OS 環境は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ。
    - Settings クラス: J-Quants / kabu ステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを提供。値検証（有効な env 値チェック）と必須 env の取得が可能。
- AI（NLP）関連
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事（raw_news, news_symbols）を銘柄ごとに集約して OpenAI（gpt-4o-mini）へ送信し、銘柄別センチメント（ai_scores）を算出して DuckDB に保存する処理を実装。
    - 時間ウィンドウ計算（JST 前日15:00～当日08:30 に対応する UTC 範囲）。
    - バッチ処理（1 API コールで最大 20 銘柄）、1 銘柄あたりの最大記事数/文字数制限、レスポンスの堅牢なバリデーション。
    - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。API 失敗時は部分スキップして継続するフェイルセーフ設計。
    - テストフック: _call_openai_api を unittest.mock.patch で差し替え可能。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（70% 重み）とマクロニュースの LLM センチメント（30% 重み）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - ma200 比率計算、マクロキーワードによるニュース抽出、OpenAI 呼び出し（gpt-4o-mini）でのセンチメント評価、リトライ/フェイルセーフ設計（API 失敗時は macro_sentiment=0.0）。
    - データ・DB 操作はトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を担保。
- データプラットフォーム（Data）
  - src/kabusys/data/calendar_management.py:
    - JPX マーケットカレンダー管理。営業日判定（is_trading_day）、翌/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 日判定（is_sq_day）等を提供。
    - market_calendar が未取得のときは曜日（平日）ベースのフォールバックを提供。
    - 夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants クライアント経由で差分取得 → 保存（バックフィル/健全性チェック含む）。
  - src/kabusys/data/pipeline.py:
    - ETL パイプラインの基盤を実装。差分取得・保存・品質チェックを想定した設計。
    - ETLResult データクラス（target_date, fetched/saved カウント, quality_issues, errors）を実装し、to_dict メソッドでシリアライズ可能。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を再エクスポート（公開インターフェース）。
- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - ファクター群の計算関数を実装: calc_momentum（1/3/6M リターン、ma200乖離）、calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、calc_value（PER, ROE）。
    - DuckDB SQL を活用して計算し、データ不足時の None 戻しやログ出力の扱いを定義。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン算出（calc_forward_returns: 任意ホライズン）、IC（calc_ic: スピアマンのランク相関）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。
    - 外部依存を持たず純粋に標準ライブラリ + DuckDB SQL で実装。
  - src/kabusys/research/__init__.py:
    - 主要関数を再エクスポートして使いやすく公開。
- テスト性・設計上の注意点（全体）
  - ルックアヘッドバイアスを防ぐため、各処理は date / target_date を明示的に受け取り、datetime.today()/date.today() の直接参照を避ける設計。
  - DuckDB を主要な永続層として想定し、トランザクションと部分書き換え（コード絞り込み）で部分失敗時のデータ保護を行う。
  - OpenAI 呼び出しに対しては専用の内部呼び出し関数を定義し、モジュール間でプライベート関数を共有しないことで結合度を低く保つ。
  - 詳細なログ出力（info/debug/warning）を組み込み、外部 API エラー時は例外を上位へ伝播する箇所とフェイルセーフで継続する箇所を明確に分離。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- API キーは呼び出し引数または環境変数（OPENAI_API_KEY）で解決。env 自動ロード時に OS 環境変数を上書きしない仕組みを採用（保護済みキーセット）。

Known issues / Notes
- AI モジュールは OpenAI（gpt-4o-mini）を前提としており、実行環境に API キーとネットワークアクセスが必要です。テスト時は内部の _call_openai_api をモックすることを推奨します。
- DuckDB バージョンの違いに起因するパラメタバインドの挙動（list バインド等）を考慮して、executemany を用いた個別 DELETE を採用しています。
- calendar_update_job / ETL 周りは外部 J-Quants クライアント（kabusys.data.jquants_client）に依存します。実運用前に API レートやスキーマ互換性の確認を推奨します。
- 一部の関数はデータ不足時に中立値（例: ma200_ratio=1.0, macro_sentiment=0.0）を使って継続する設計です。これは安全側のデフォルトであり、運用方針によっては挙動変更が必要です。

今後の予定（提案）
- ai モジュールの追加メトリクス（信頼区間・応答検証の強化）。
- ETL の差分取得ロジックの可視化ダッシュボード化とスケジューリング連携。
- 単体テスト・統合テストの充実（DuckDB テストフィクスチャ・OpenAI モックを含む）。

-- End of changelog --