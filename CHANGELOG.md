CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージエントリポイント: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - サポート項目:
    - J-Quants / kabuステーション / Slack / DB パス (DuckDB / SQLite) / 監視閾値 / 実行環境 (development/paper_trading/live) / ログレベル。
  - .env 自動読み込み機能:
    - プロジェクトルート（.git または pyproject.toml）を起点に .env, .env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env.local は .env 上書き（ただし OS 環境変数は protected として上書き不可）。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無での違い）に対応。
  - 環境変数未設定時は明確なエラーメッセージを返す _require() を実装。
- AI モジュール (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを算出。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄処理）、各銘柄は最大記事数/文字数でトリム。
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 書き換え（対象コードのみ DELETE → INSERT）を実装。
    - DuckDB の executemany 空リスト制約を考慮して空チェックを追加。
    - JSON パースの堅牢化（余分な前後テキストが混入する場合に最外の {} を抽出して復元）。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロキーワードで記事を抽出し OpenAI（gpt-4o-mini）へ送信。API 失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - レジームスコアのクリップと閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性を考慮し OpenAI 呼び出しは差し替え可能に設計。
- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダーの夜間バッチ更新処理 (calendar_update_job) と、営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - 市場カレンダーがない場合は曜日ベースのフォールバック（平日を営業日とみなす）。
    - DB 登録優先の判定ロジック、探索上限 (_MAX_SEARCH_DAYS=60)、バックフィル期間、健全性チェックを実装。
    - J-Quants クライアント経由での取得・保存処理を想定。
  - pipeline / etl:
    - ETLResult データクラスを実装し public API（kabusys.data.etl）で再エクスポート。
    - 差分更新・バックフィル・品質チェックの結果・エラー集約を表現。
    - DuckDB テーブル存在チェックや最大日付取得等の内部ユーティリティを実装（ETL の基礎機能）。
- リサーチ (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER/ROE）を DuckDB 上で計算する関数を追加:
      - calc_momentum, calc_volatility, calc_value
    - データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）、IC（Spearman）計算 calc_ic、rank / factor_summary 等の統計ユーティリティを追加。
    - pandas 等外部依存を持たない純標準ライブラリ実装。
- パッケージエクスポート整理
  - 各サブパッケージで主要関数を __all__ にて公開（例: kabusys.ai.score_news, kabusys.research.* 等）。

Changed
- OpenAI 統合観点での設計選択を明確化:
  - gpt-4o-mini をデフォルトモデルに指定、JSON Mode（response_format={"type": "json_object"}）を利用して構造化レスポンス受け取りを優先。
  - news_nlp と regime_detector は内部で独立した _call_openai_api を持ち、モジュール間のプライベート関数共有を避ける設計に変更。

Fixed / Robustness
- DuckDB の実運用上の互換性対応:
  - executemany に空リストを渡すと失敗する問題に対し空チェックを追加して回避。
- OpenAI レスポンス処理の堅牢化:
  - JSON パース失敗時のフォールバック処理（外側の {} を抽出して再パース）を実装。
  - API の各種エラー（RateLimit, Connection, Timeout, 5xx）に対するリトライ/フォールバック戦略を統一。

Notes / Design decisions
- ルックアヘッドバイアス防止:
  - すべての分析/スコア計算関数で datetime.today() / date.today() を直接参照せず、target_date 引数を明示的に受け取る設計。
  - DB クエリは target_date より前 / 排他条件を厳守する。
- フェイルセーフ方針:
  - 外部 API（OpenAI / J-Quants）失敗時は可能な限り処理を継続し、該当結果をスキップまたはデフォルト値で補完する（致命的な例外は呼び出し側へ伝播）。
- DuckDB を第一クラスに想定:
  - SQL ウィンドウ関数や ROW_NUMBER / LEAD/LAG 等を多用し、DuckDB 接続を直接受け取る API を設計。

Known issues / TODO
- pipeline._get_max_date の末尾付近にソース断片（date.fro）と思われる不完全な箇所が存在します。現状のままだとこの関数の最後の戻り処理が未完・バグを含む可能性があるため、実運用前に要修正。  
  （提供されたスナップショットに基づく注記）

Security
- 機密情報（OpenAI API key 等）は Settings にて環境変数から取得する設計。自動 .env ロードは環境変数優先・.env.local の上書き制御を行うことで意図しない上書きを防止。

Acknowledgements / Notes for integrators
- OpenAI 呼び出し部はテスト容易性を考慮して差し替え可能（ユニットテストでのモックが可能）。
- DuckDB のバージョン差異（特に executemany の挙動）を考慮した実装が含まれます。実行環境の DuckDB バージョンで動作確認を推奨します。

-----------------------------------------------------------------------------
今後の予定（非網羅）
- pipeline._get_max_date の修正と ETL 周りの単体テスト充実化
- metrics / モニタリング（監視アラートの具体化）
- 実運用に向けた OpenAI レート管理・コスト制御オプションの追加

-----------------------------------------------------------------------------
リリース作成者: コードベース解析に基づく推定まとめ（CHANGELOG はコード内容から推測して作成）