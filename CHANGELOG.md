Keep a Changelog
=================

すべての注目すべき変更を時系列で記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

注意: 下記の変更内容はリポジトリ内のソースコードから推測してまとめたものであり、実際のコミット履歴ではありません。

Unreleased
----------

- なし

0.1.0 - 2026-04-03
------------------

Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョン: 0.1.0。公開モジュール: data, strategy, execution, monitoring。
- 設定 / 環境変数管理
  - .env ファイルと環境変数の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git or pyproject.toml から探索して .env / .env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - export KEY=val 形式やクォート付き値、インラインコメント等に対応する堅牢な行パーサを実装。
    - .env.local を .env より優先して上書きする挙動（ただし OS の既存環境変数は保護）。
    - 設定読み取り用 Settings クラスを公開。J-Quants / kabu / LINE / DB パス / 監視閾値 / ログレベル等のプロパティを提供。環境値検証（例: KABUSYS_ENV / LOG_LEVEL のバリデーション）を実装。
- AI（自然言語処理）機能
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を行う score_news(conn, target_date, api_key=None) を実装。
    - バッチサイズ、記事数・文字数トリム、JSON レスポンスの堅牢な検証、スコアの ±1.0 クリップ、失敗時のフォールバック動作を実装。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで処理。
    - calc_news_window(target_date) により JST ベースのニュース収集ウィンドウを UTC naive datetime で計算。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime(conn, target_date, api_key=None) を実装。
    - マクロキーワードでニュースを抽出し、OpenAI による JSON レスポンス取得とパースを行う。API失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - OpenAI 呼び出しは各モジュールで独立実装（モジュール間のプライベート関数共有を避ける設計）。
- データ処理 / ETL / カレンダー
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの有無に応じた営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。DB の登録値を優先し未登録日は曜日ベースでフォールバック。
    - calendar_update_job(conn, lookahead_days=...) で J-Quants API から差分取得→保存（バックフィル、健全性チェックを含む）。
    - 最大探索日数・先読み・バックフィル・サニティチェック等の安全装置を導入。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー概要を保持）。to_dict() により品質問題を辞書化して出力可能。
    - 差分取得、保存（jquants_client 経由での冪等保存）、品質チェックのフローを想定した設計（詳細実装は jquants_client / quality モジュールに依存）。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。
- 研究（Research）ライブラリ
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value を実装。各関数は DuckDB の prices_daily / raw_financials を参照して日次で (date, code) ベースの辞書リストを返す。
    - 計算対象: 短中長期モメンタム、200日移動平均乖離、ATR20、相対ATR、平均売買代金、出来高比、PER/ROE（財務データとの結合）など。
    - データ不足時には None を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None) による将来リターン計算（複数ホライズン対応、入力検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col) による Spearman（ランク）IC 計算（同順位は平均ランクで処理）。
    - rank(), factor_summary() によりランク変換・基本統計量（count/mean/std/min/max/median）を算出。
    - Pandas 等外部ライブラリに依存せず純粋 Python + DuckDB で実装。
- その他ユーティリティ
  - duckdb を前提とした SQL 実行と型変換ユーティリティ（例: _to_date）を多数実装し、DB 結果の扱いを一貫化。
  - ロギングを広範に採用し、フェイルセーフや診断のための情報を出力する設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし（実装内に多数のフェイルセーフ・エラーハンドリングを含む）。

Deprecated
- なし

Removed
- なし

Security
- 初期リリースのため該当なし。注意点:
  - OpenAI API キー等のシークレットは環境変数経由で取得する設計（Settings クラス）。.env 自動読み込み時も OS 環境変数は保護されるよう配慮あり。
  - .env ファイルの取り扱いでファイル読み込みエラー時に警告を出す実装あり。

設計ノート（実装から読み取れる重要な振る舞い）
- ルックアヘッドバイアス対策: 各スコアリング / 指標計算関数は date.today() に依存せず、引数で与えられる target_date に対して過去データのみを参照する設計になっている。
- フェイルセーフ: 外部API（OpenAI / J-Quants）障害時はスコアに中立値を使う、または該当チャンクをスキップして残りを継続する方針。
- 冪等性: DB への更新は基本的に冪等化（DELETE → INSERT、ON CONFLICT 相当）を意識して実装されている。
- テスト性: OpenAI 呼び出し部分はモジュール内部の _call_openai_api を patch して差し替え可能な形で実装されており、ユニットテストでのモックが容易。

今後の改善候補（ソースから推測）
- strategy / execution / monitoring モジュールの具体的実装（現状はパッケージ公開のみ）。
- テストケースと型アサーションの拡充（特に OpenAI レスポンスの境界ケース）。
- jquants_client / quality モジュールの実装・テスト（ETL ワークフローの完全化）。
- エラーメトリクス収集（外部サービス連携）やリトライポリシーのチューニング。

--- 

以上。必要であれば、各変更項目をコミット単位（想定コミットメッセージ）に分解したり、英語版の CHANGELOG を作成したりできます。どの粒度で出力するか指示してください。