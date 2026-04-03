CHANGELOG
=========

すべての変更は「Keep a Changelog」準拠の形式で記載しています。  
このファイルはコードベースの内容から推測して作成しています（実装上の意図や設計方針を読み取り要約）。不明点は実際のコミット履歴を参照してください。

[Unreleased]
------------

- （現時点の開発中の変更はここに記載します）

[0.1.0] - 2026-04-03
-------------------

Added
- 初回リリースを公開。
- パッケージ構成の追加・公開:
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開サブパッケージ: data, strategy, execution, monitoring。
- 設定・環境変数管理:
  - kabusys.config:
    - .env ファイル / .env.local の自動読み込み機能を実装。プロジェクトルート検出は .git / pyproject.toml を基準に行い、CWD に依存しない安全な検索を実装。
    - .env パースロジックはコメント行、export プレフィックス、クォート文字内のエスケープ、インラインコメント判定（クォートあり/なしで挙動を分ける）に対応。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
    - 環境変数取得ラッパー Settings を実装。必須値チェック（_require）や型変換、既定値、検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を提供。
    - 各種設定プロパティを公開（J-Quants・kabu API・LINE・データベースパス・監視閾値・ログ/環境判定など）。
- AI モジュール（OpenAI 経由の NLP / レジーム判定）:
  - kabusys.ai.news_nlp:
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols から記事を集約し、gpt-4o-mini を用いて銘柄ごとのセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 を UTC に変換）を提供（calc_news_window）。
    - 入力トリム（記事数上限・文字数上限）とチャンク単位（最大20銘柄）でのバッチ送信を実装。
    - JSON Mode のレスポンスを頑健にパースし、レスポンスバリデーション（results リスト・コード整合性・数値チェック）を行う。
    - 429・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフのリトライ実装。部分失敗を許容し、成功分のみ ai_scores を置換（DELETE → INSERT）することで冪等性と部分障害耐性を確保。
    - DuckDB の executemany に関する仕様対策（空リストでの executemany を避けるガード）。
  - kabusys.ai.regime_detector:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、market_regime テーブルへ書き込む。
    - 1321 の MA200 乖離計算（ルックアヘッド回避のため target_date 未満のデータのみ使用）。データ不足時は中立(1.0)を返すフェイルセーフ。
    - マクロキーワードでフィルタした記事タイトル抽出、LLM 呼び出し（gpt-4o-mini）による macro_sentiment 評価（JSON レスポンス期待）。
    - API エラーやパース失敗の際は macro_sentiment=0.0 にフォールバックし処理を継続（フェイルセーフ）。書き込みは冪等に BEGIN/DELETE/INSERT/COMMIT を行い、例外時は ROLLBACK。
    - OpenAI 呼び出し部分はテスト時に差し替え可能なように内部関数化。
- データ層（Data Platform）:
  - kabusys.data.calendar_management:
    - JPX 市場カレンダー管理機能を提供。market_calendar テーブルの有無に応じた営業日判定（is_trading_day）、前後営業日の取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 判定（is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。最大探索日数制限で無限ループを防止。
    - 夜間バッチ更新ジョブ calendar_update_job を提供。J-Quants から差分取得し、バックフィル／健全性チェック（将来日付が過度にずれている場合のスキップ）を実装。
  - kabusys.data.pipeline / etl:
    - ETLResult データクラスを実装し ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返す。
    - pipeline の ETLResult を etl モジュールで再エクスポート。
    - ETL パイプラインの設計方針に沿った差分取得・バックフィル・品質チェックの骨格実装（jquants_client 経由の取得/保存、品質チェック収集）。
- リサーチ（研究用）モジュール:
  - kabusys.research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照してモメンタム・ATR・流動性・PER/ROE 等を計算し、(date, code) 単位の辞書リストを返す。欠損・データ不足の取り扱いを明確化。
  - kabusys.research.feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン一括取得）、calc_ic（スピアマンのランク相関による IC 計算）、factor_summary（基本統計量算出）、rank（同順位の平均ランク）を提供。
  - kabusys.research.__init__ で主要関数を公開。zscore_normalize を data.stats から re-export。
- 汎用実装・運用上の配慮:
  - ルックアヘッドバイアス対策として、各種処理は datetime.today()/date.today() を参照しない（target_date ベースで deterministic に動作）。
  - DuckDB を用いた SQL + Python ハイブリッド実装。SQL 内でウィンドウ関数や LAG/LEAD を活用して効率的に算出。
  - ロギングと警告出力を多用してフェイルセーフ時の理由を記録。

Changed
- 初回リリースのため該当なし（初期実装）。

Fixed
- 初回リリースのため該当なし（初期実装）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは引数で注入可能 / 環境変数 OPENAI_API_KEY で解決。キー未設定時は明示的な ValueError を発生させることで秘密情報の誤使用を防止。

Notes / 既知の制限
- 日付処理は明示的に timezone-naive な date / datetime を使用しており、UTC/JST の扱いに注意が必要。API／DB 側の日付保存規約に依存します。
- OpenAI 関連は gpt-4o-mini を前提としたプロンプト設計（JSON Mode 想定）。モデルや SDK の将来的な仕様変更により影響を受ける可能性があります。
- DuckDB のバージョン差異に起因する挙動（executemany の空リスト取り扱い等）は考慮済みだが、環境差異で追加対応が必要になる場合があります。
- .env の自動ロードはプロジェクトルート検出に失敗した場合はスキップされます。テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

Authors
- コードベースのコメントと実装から推測して本 CHANGELOG を作成しました。実際のコミットログ・リリースノートがある場合はそちらを優先してください。