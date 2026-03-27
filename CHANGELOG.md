CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

Unreleased
----------

（なし）

[0.1.0] - 2026-03-27
-------------------

Added
- 初回リリース。日本株自動売買プラットフォームのコアライブラリを追加。
  - パッケージエントリポイント:
    - kabusys パッケージ（__version__ = 0.1.0）
    - 公開サブパッケージ: data, strategy, execution, monitoring

- 環境設定 / ロード
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを追加。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート無しでは '#' の直前が空白/タブのときのみコメントとみなす）
  - Settings クラスを提供（環境変数をプロパティとして取得・バリデーション）
    - J-Quants / kabuステーション / Slack / データベースパス設定（duckdb/sqlite）等
    - KABUSYS_ENV（development/paper_trading/live）の検証
    - LOG_LEVEL の検証
    - is_live / is_paper / is_dev の便宜プロパティ

- データプラットフォーム（data）
  - calendar_management:
    - market_calendar を使った営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB に値がない場合は曜日（平日）ベースでフォールバック
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）
  - pipeline / etl:
    - ETLResult データクラスによる ETL 実行結果管理（品質チェック情報・エラー収集を含む）
    - 差分取得・バックフィル・品質チェック方針を実装
    - etl モジュールで ETLResult を再エクスポート

- AI モジュール（ai）
  - news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとに gpt-4o-mini を用いてセンチメント（-1.0〜1.0）を算出する score_news を実装
    - JST ベースのニュースウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換して比較）
    - 1チャンクあたり最大20銘柄、各銘柄は最新10記事かつ3000文字にトリム
    - JSON Mode を利用したレスポンス検証・パース処理（冗長テキスト復元ロジック含む）
    - レート制限 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
    - スコアは ±1.0 にクリップ。書き込みは対象コードのみ DELETE → INSERT で冪等に実行（部分失敗時に他銘柄の既存スコアを保護）
    - テスト用に内部の OpenAI 呼び出しをモックしやすい実装（_call_openai_api の差し替え想定）
  - regime_detector:
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出する score_regime を実装
    - マクロ記事抽出はニューステーブルからマクロキーワードでフィルタ（最大20件）
    - LLM（gpt-4o-mini）呼び出しとレスポンスパースの実装（news_nlp と意図的に実装を分離）
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフ、リトライ/バックオフを実装
    - レジームスコア合成、閾値によりラベル付け、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - ルックアヘッドバイアス対策（target_date 未満のみ参照、datetime.today()/date.today() を参照しない方針）

- リサーチ（research）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を prices_daily から計算
    - calc_volatility: 20日 ATR（atr_20）, 相対ATR（atr_pct）, 20日平均売買代金（avg_turnover）, 出来高比（volume_ratio）を計算
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が無効な場合は None）
    - 全関数は DuckDB を受け取り SQL を主体に実装、結果は (date, code) をキーとする辞書リストで返却
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括 SQL で取得（horizons の検証あり）
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。データ不足時は None を返す
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めを行い浮動小数誤差に対処）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - 外部依存を持たない実装（pandas 等に依存せず標準ライブラリ + duckdb）

Other notes / implementation details
- DuckDB を主要なデータストアとして想定。多くの関数は duckdb.DuckDBPyConnection を引数に受け、一貫して SQL を利用して計算/読み書き。
- OpenAI SDK（OpenAI クライアント）を用いた JSON Mode の活用と厳密なレスポンス検証を行う設計。
- API 呼び出し周りはリトライ・バックオフ・5xx の扱いなどを明示し、フェイルセーフで継続するよう実装（部分失敗が全体を破壊しないよう配慮）。
- テスト容易性を考慮し、内部の API 呼出関数は差し替え可能（unittest.mock.patch を想定）。

Fixed
- 初回リリースのため該当なし。

Changed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes for users
- OpenAI API キーは score_news / score_regime の api_key 引数または環境変数 OPENAI_API_KEY により供給してください。設定がない場合は ValueError を送出します。
- .env 自動読み込みはパッケージ配布環境でも動作するようプロジェクトルート探索を行いますが、テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

ライセンスや既知の制約、将来のマイルストーン（例: PBR/配当利回りの追加、さらに精緻な品質チェック等）は別途ドキュメントにまとめる予定です。