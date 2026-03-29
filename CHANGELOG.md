CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
-------------------

初期リリース。日本株自動売買システム「KabuSys」の基本機能群を提供します。主要な追加点は以下の通りです。

Added
- パッケージ基礎
  - パッケージバージョン: kabusys.__version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定/ロード機能 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数からの設定読み込み（自動読み込みあり）。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に探索し、CWD に依存しない実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープ対応
    - インラインコメントの取り扱い（クォートの有無により異なる挙動）
  - .env の読み込み挙動:
    - デフォルト: OS 環境変数 > .env.local > .env の優先度
    - override/protected 機能により OS 環境変数の上書きを防止
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DBパス 等のプロパティを提供
    - 必須環境変数未設定時は _require() が ValueError を送出
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/...）

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を銘柄別に集約し OpenAI API（gpt-4o-mini）でセンチメント評価
    - API レート制限・ネットワーク断・5xx などに対する指数バックオフ（再試行）実装
    - JSON Mode のレスポンスパースおよび復元処理（前後ノイズを含む場合の {} 抽出）
    - スコアのバリデーション、±1.0 でのクリップ
    - バッチ処理（最大20銘柄）と銘柄ごとトリム(_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - DuckDB への冪等書き込み（部分失敗時に既存スコアを保護するため、該当コードのみ DELETE → INSERT）
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照せず、呼び出し元の target_date を利用

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定
    - マクロキーワードで raw_news をフィルタし LLM により -1.0〜1.0 の macro_sentiment を取得
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 で継続（フェイルセーフ）
    - レジームのラベル化（bull / neutral / bear）と DuckDB の market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - OpenAI クライアントの注入（api_key 引数または環境変数 OPENAI_API_KEY）

  - 両モジュール共通設計方針
    - OpenAI 呼び出しはモジュールごとに独立実装（内部ヘルパー関数を共有しない）
    - テスト容易性のため _call_openai_api を patch して差し替え可能
    - 再試行時のログ出力、失敗時の安全なフォールバック

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを利用した営業日判定 API:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB にデータがない場合は曜日ベース（平日を営業日）でフォールバック
    - 最大探索範囲 (_MAX_SEARCH_DAYS) の導入により無限ループ回避
    - calendar_update_job により J-Quants から差分取得・バックフィル・健全性チェックを実行し market_calendar を更新
    - DB 値優先・未登録日は曜日フォールバックという一貫した方針

  - ETL パイプライン (pipeline.ETLResult, etl モジュール)
    - ETLResult データクラスを公開 (kabusys.data.etl から再エクスポート)
    - ETLResult は取得件数・保存件数・品質問題リスト・エラーリスト等を保持
    - has_errors / has_quality_errors / to_dict のユーティリティを提供
    - 差分取得、バックフィル、品質チェック、J-Quants クライアント連携等の設計に準拠した実装方針をドキュメント化

- Research（研究用）モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - calc_value: PER, ROE（raw_financials を利用）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - 各関数は prices_daily / raw_financials のみ参照し、本番口座や発注 API にはアクセスしない
    - データ不足時の None 処理、ログ出力

  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 任意ホライズンの将来リターン（デフォルト [1,5,21]）
    - calc_ic: Spearman ランク相関（IC）計算（少数データ・同順位対応）
    - rank: 平均ランク付け（同順位は平均ランク）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出
    - パフォーマンスと安全性（horizons の検証、スキャンレンジの制限等）を考慮した実装

Changed
- 新規リリースのため該当なし

Fixed
- 新規リリースのため該当なし

Security
- OpenAI API キーの取り扱い:
  - api_key 引数が優先、未指定時は OPENAI_API_KEY 環境変数を参照
  - 必須未設定時は ValueError を明示的に送出し、無許可の呼び出しを防止

Notes / 注意事項
- 自動 .env 読み込みはプロジェクトルートを基準とするため、配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化することを推奨します。
- DuckDB への executemany 実行は空リストを渡すとエラーになるバージョンがあるため、実行前に空チェックを行っています（互換性対応）。
- AI モジュールは外部 API（OpenAI）に依存するため、API コスト・レート制限に注意してください。失敗時のフェイルセーフ動作（スコア 0.0、または該当銘柄スキップ）が実装されていますが、運用設計に合わせた監視・アラート設定を推奨します。
- すべての関数はルックアヘッドバイアス防止のために target_date ベースで動作し、内部で date.today() / datetime.today() を直接使わない設計になっています。

ライセンス等
- 本リリースのライセンス・貢献ガイドライン等はリポジトリのトップレベルファイルを参照してください。