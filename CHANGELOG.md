KEEP A CHANGELOG
=================

すべての注目すべき変更点をこのファイルに記録します。慣例に従い、バージョン別に「Added / Changed / Fixed / Deprecated / Removed / Security」などで分類しています。

フォーマットは Keep a Changelog に準拠しています。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-04
-------------------

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

Added
- パッケージ初期化
  - kabusys パッケージの基本情報を追加（__version__ = "0.1.0"）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 / ロード機構（kabusys.config）
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダーを実装。
    - 自動検出: パッケージの位置から .git または pyproject.toml を起点にプロジェクトルートを探索。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの堅牢化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い、キー/値検証等を実装。
  - Settings クラスを導入（settings インスタンスで利用可能）。
    - J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / ログ環境等の設定プロパティを提供。
    - 必須キー未設定時は ValueError を発生。
    - KABUSYS_ENV, LOG_LEVEL の値検証（許容値チェック）。
    - Path 型の返却・bool フラグ等のユーティリティ。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む機能を実装。
  - 主な機能:
    - ニュース収集ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30）。
    - 銘柄ごとに最新記事を最大件数・文字数でトリムしてプロンプト生成。
    - 最大 20 銘柄/チャンク単位でのバッチ送信。
    - レスポンスのJSONバリデーションとスコアクリップ（±1.0）。
    - エラー時のフェイルセーフ（API 呼び出し失敗はスキップし処理継続）。
    - リトライ（429／ネットワーク断／タイムアウト／5xx）・指数バックオフ。
    - DuckDB 互換を考慮した安全な DELETE/INSERT の冪等処理（部分失敗時に既存スコアを保護）。
  - テスト容易性:
    - OpenAI 呼び出し部分を _call_openai_api で分離しており、ユニットテストで差し替え可能。

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市況レジーム（bull / neutral / bear）を判定し market_regime テーブルへ書き込む実装。
  - 主な機能:
    - ma200_ratio 計算（target_date 未満のデータのみ使用してルックアヘッドバイアスを防止）。
    - マクロキーワードによる raw_news フィルタリング。
    - OpenAI 呼び出し（JSON mode）とレスポンスパース、リトライ／フォールバック（API 失敗時は macro_sentiment=0.0）。
    - レジームスコア合成と閾値によるラベリング。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）。

- リサーチモジュール（kabusys.research）
  - 基本ファクター群と探索用ユーティリティを実装。
    - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）。
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時の None 処理）。
      - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
      - Value: PER, ROE（raw_financials の最新報告データを使用）。
    - feature_exploration: calc_forward_returns（任意ホライズン）、calc_ic（Spearman ランク相関）、factor_summary（統計量）、rank（同順位は平均ランク）
    - research パッケージの __all__ で主要関数を再エクスポート。
  - 設計方針:
    - DuckDB を使った SQL + Python 実装、外部 API/発注へのアクセスはしない。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日判定ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の API を実装。
    - DB 優先 + 未登録日への曜日ベースフォールバック、最大探索日数制限による安全策。
    - 夜間バッチ更新 job (calendar_update_job)：J-Quants クライアントを使った差分取得、バックフィル、健全性チェック、保存処理。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の集約）を実装し、公開インターフェースを提供。
    - ETL 設計: 差分取得、idempotent 保存、品質チェック（quality モジュール）を想定。

- DuckDB を単一の主要な分析 DB として採用し、各モジュールは DuckDB 接続オブジェクトを受け取る形で実装（テストしやすさ、環境分離を考慮）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数読み込みにおける OS 環境保護機能:
  - .env 読み込み時に既存 OS 環境変数キーを protected として扱い、必要に応じて上書き禁止（override オプションを考慮）。
- OpenAI API キーの注入は引数で上書き可能（テスト時の差し替え・秘密情報注入を容易にする設計）。
- 必須環境変数未設定時は明確なエラーメッセージを出力して処理を中断。

Notes / Implementation details
- OpenAI 呼び出し周りは JSON Mode を利用し、レスポンスの厳密な JSON パースを試みた上でフォールバック（文字列から最外の {} を抽出して再パース）する堅牢化を実施。
- LLM 呼び出しはリトライ・エクスポネンシャルバックオフを行い、最終的に失敗した場合は「スコア 0.0 にフォールバック」または「当該チャンクをスキップ」するフェイルセーフを採用。
- 時刻関連の窓（ニュースウィンドウ等）は JST ベースで定義し内部では UTC naive datetime を返す（DB 内の UTC 時刻と比較するため）。
- DuckDB バインド/ executemany の互換性に配慮した実装（空リストでの executemany 回避など）。
- 各モジュールはユニットテストで差し替え可能なフック（例: _call_openai_api）を提供している。

Acknowledgements / External APIs
- OpenAI（gpt-4o-mini）をセンチメント分析で利用する設計。
- J-Quants API をデータ取得・カレンダー更新に利用する前提（kabusys.data.jquants_client を利用）。

今後の予定（例）
- strategy / execution / monitoring の具現化（現在はパッケージ定義のみ）。
- 追加ファクター・統計分析機能の拡張。
- より詳細な品質チェック（quality モジュール）の強化と監査ログの整備。
- CI / テストカバレッジの拡充、ドキュメントの整備（ユーザー向け設定手順等）。

---------- 

注: 本 CHANGELOG は提供されたコードベースの実装内容（docstring とソース）から推測して作成しています。実際のリリースノートとして配布する場合は、リリース済みのコミット履歴やプロジェクトマネージャの記録に基づき調整してください。