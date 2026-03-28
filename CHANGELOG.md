CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
以下は、与えられたコードベースから推測して作成した変更履歴（初期リリース相当）です。

Unreleased
----------

- （現状なし）

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報を src/kabusys/__init__.py に定義（__version__ = "0.1.0"）。
  - top-level の公開モジュール名として data, strategy, execution, monitoring を列挙。

- 環境設定 / 設定管理
  - src/kabusys/config.py を追加。
    - .env ファイル（.env, .env.local）と OS 環境変数から自動的に読み込む仕組みを実装。
    - プロジェクトルート探索を __file__ 基点で行う _find_project_root を実装し、CWD に依存しない自動ロード。
    - .env 行パーサー（クォート、バックスラッシュエスケープ、export プレフィックス、インラインコメントの扱い）実装。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等をプロパティ経由で取得。未設定必須項目は ValueError を送出。

- AI 関連
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を LLM（gpt-4o-mini）で銘柄毎にセンチメント化し ai_scores テーブルへ書き込む score_news を追加。
    - タイムウィンドウ計算（JST 換算）、1 銘柄あたりの記事数・文字数制限、最大バッチサイズ、JSON Mode を使った厳密レスポンス想定などの実装。
    - API エラー（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフ再試行、レスポンスバリデーション、スコアのクリップ（±1.0）、部分成功時の安全な DB 書き換え（DELETE → INSERT）を実装。
    - 単体テスト容易性のため _call_openai_api を独立実装し patch による差し替えを想定。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ma200 計算でルックアヘッドバイアスを回避（target_date 未満のみ使用）、マクロニュース抽出、OpenAI 呼出し（gpt-4o-mini）、再試行・フェイルセーフ（API 失敗時 macro_sentiment=0.0）、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - マクロキーワードリスト、モデル指定、リトライポリシー等の設定定数を用意。

- Research（研究）機能
  - src/kabusys/research パッケージを追加。
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value を実装。すべて DuckDB を用いた SQL クエリで計算し、prices_daily / raw_financials を参照。結果は (date, code) をキーとする辞書リストで返す。
      - モメンタム（1M/3M/6M）、200 日 MA 乖離、20 日 ATR、平均売買代金、出来高比率、PER/ROE（財務データから）を計算。
    - feature_exploration.py
      - calc_forward_returns（任意ホライズン）、calc_ic（Spearman の ρ による IC）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。pandas 等に依存せず純粋な標準ライブラリ＋DuckDB で実装。
    - src/kabusys/research/__init__.py で主要関数群と data.stats.zscore_normalize を公開。

- Data（データ基盤）機能
  - src/kabusys/data パッケージを追加。
    - calendar_management.py
      - market_calendar を利用した営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB に登録されている値を優先し、未登録日は曜日ベースでフォールバックする一貫性を持った実装。
      - calendar_update_job により J-Quants API (jquants_client) から差分取得 → 冪等保存を行うバッチ処理を提供。バックフィル、健全性チェック、エラーハンドリングを備える。
    - pipeline.py
      - ETL の上位インターフェースとヘルパーを実装。差分更新、バックフィル、品質チェックフックを想定。
      - ETLResult dataclass を追加（target_date / 取得件数 / 保存件数 / quality_issues / errors 等を含む）。to_dict により品質問題をシリアライズ可能。
    - etl.py で ETLResult を再エクスポート。
    - DuckDB 周りの互換性（table 存在確認、MAX(date) 取得等）や executemany に対する空リスト回避などの実装上の注意を反映。

- 安全性・運用性
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT を想定）し、トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - LLM 呼び出しや外部 API 呼び出しはリトライ・バックオフ・ログ記録・フェイルセーフ（スコア 0.0 等）を備え、運用上の安定性を考慮。
  - テストフレンドリーな設計（内部 _call_openai_api の差し替えポイントなど）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし（実装段階で DuckDB executemany の空リスト問題などに対処済み）。

Notes / 実装上の注意
- すべての時間・日付関連処理はルックアヘッドバイアスを防ぐために datetime.today()/date.today() を参照しない設計を意識（関数は target_date を明示的に受け取る）。ただし calendar_update_job 等は実行時の today() を参照してカレンダー取得範囲を計算する。
- OpenAI クライアントは openai.OpenAI を利用し、JSON Mode（response_format={"type":"json_object"}）を期待。レスポンスの不正やパースエラーは警告ログを出してスキップする設計。
- 一部ファイルにはテスト用の差し替えポイント（unittest.mock.patch）やログ出力が意図的に配置されている。
- strategy / execution / monitoring はパッケージの公開名として __all__ に列挙されているが、今回のコードベースに完全な実装は見当たらないため（将来実装予定のエントリポイントとして扱われる可能性あり）。

Acknowledgements
- DuckDB をデータ処理基盤として採用。
- OpenAI（gpt-4o-mini）をニュース解析／センチメント評価に使用する設計。

今後の課題（候補）
- strategy / execution / monitoring 各モジュールの具現化（発注ロジック、監視・通知、実行エンジン）。
- ai/regime_detector と ai/news_nlp の統合テスト・エンドツーエンド検証（LLM レスポンスパターンに対する堅牢性強化）。
- カレンダー・ETL の運用メトリクスと自動リトライ監視の強化。