CHANGELOG
=========
すべての日付/バージョンはコードベースから推測して作成しています。
フォーマットは「Keep a Changelog」準拠です。

Unreleased
----------
- （今後の変更をここに記載）

0.1.0 - 2026-04-04
-----------------
Added
- パッケージ初期リリース。kabusys のコア機能を実装。
  - パッケージメタ情報:
    - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。
  - 設定管理:
    - src/kabusys/config.py
      - .env（.env.local を上書き）およびOS環境変数から設定を自動読み込みする仕組みを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
      - .env パーサ実装（export 形式対応、クォートとエスケープ処理、インラインコメント処理）。
      - 必須環境変数取得用の _require と Settings クラスを提供。J-Quants / kabu API / LINE / DB /監視/ロギング等の設定プロパティを含む。
      - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。
  - AI 関連:
    - src/kabusys/ai/news_nlp.py
      - ニュース記事群を OpenAI（gpt-4o-mini, JSON Mode）でバッチ評価し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST）と記事集約、チャンクバッチ処理、レスポンスバリデーション、スコアクリップを実装。
      - リトライ（429/ネットワーク/タイムアウト/5xx）で指数バックオフを行うフェイルセーフ設計。
      - テスト容易性のため API 呼び出し点を差し替え可能に実装。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算し market_regime テーブルへ冪等書き込みする処理を実装。
      - LLM 呼び出しのリトライ/フェイルセーフ、レスポンスパースの堅牢化を実装。
  - Data / ETL / カレンダー / パイプライン:
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
      - market_calendar テーブル存在時は DB 値優先、未登録日は曜日ベースのフォールバックを行う一貫したロジック。
      - calendar_update_job により J-Quants から差分取得→冪等保存（backfill, sanity check を含む）。
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
      - ETLResult データクラスを公開（パイプラインの取得数/保存数/品質問題/エラーを集約）。
      - 差分更新・バックフィル・品質チェック方針を備えた ETL パイプラインの基盤ロジックを実装（jquants_client と quality モジュールを利用する想定）。
  - Research（因子・特徴量解析）:
    - src/kabusys/research/* による因子計算と特徴量探索ユーティリティを追加。
      - factor_research.calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を基にモメンタム、ボラティリティ、バリュー系因子を計算。
      - feature_exploration.calc_forward_returns: 将来リターン取得（任意ホライズン）。
      - feature_exploration.calc_ic / rank / factor_summary: IC（Spearman ρ）計算、ランク変換、統計サマリー。
      - zscore_normalize を data.stats から再エクスポートする初期統合。
  - データユーティリティ:
    - DuckDB を前提とした SQL 実装が多く、日付変換ユーティリティやテーブル存在チェック等を整備。
  - ロギングと設計方針:
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計（関数に target_date を渡す方式）。
    - DB 書き込みは冪等性を重視（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の構成）。
    - OpenAI 呼び出しや外部 API 呼び出し失敗時は例外を拡散しないフェイルセーフ挙動（一部は警告ログにフォールバック）を採用。

Changed
- （初回リリースのためなし）

Fixed
- .env パーサの堅牢化:
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、不正行のスキップ等に対応。
- OpenAI レスポンスのパース耐性向上:
  - gpt の JSON mode でも前後に余計なテキストが混在するケースを考慮して最外側の { } を抽出して復元する実装を追加。
- DuckDB executemany の空リスト制約への対応:
  - executemany を呼ぶ前に空リストかどうかをチェックして回避する処理を追加（互換性対策）。

Security
- API キーの取り扱い:
  - OpenAI API キーは関数引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定の場合は ValueError を発生させる明示的なチェックを実装。
- 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや CI 用の安全措置）。
- 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を導入し、不正な値を早期検出。

Notes / Implementation details
- OpenAI へのリクエスト関数は各モジュールで独立実装されており、テスト時は unittest.mock.patch で差し替え可能。
- 多くの処理でフェイルセーフ（API失敗時はスコア0.0やスキップ）を採用しており、本番での頑健性を重視。
- 時刻の扱い:
  - ニュースウィンドウは JST を基準に内部では UTC naive datetime を使って DB と比較する方針（calc_news_window の実装参照）。
- 最大リトライ回数・バックオフ初期値・バッチサイズ・ウィンドウ定義などは定数化されており、調整可能。

Acknowledgements / TODO
- 今後のリリースで考慮すべき点（例）:
  - ai モジュールの OpenAI SDK 互換テスト（SDK の将来変更に対する回帰テスト）。
  - より細かい品質チェック結果のポリシー（ETL の自動中断閾値等）。
  - パフォーマンス向上（DuckDB クエリのインデックスやパラレル化検討）。

以上。追加のリリースノート要望（別の日付でのバージョン分割や細かい修正履歴化）や、特定モジュールに対する詳細な変更点追記が必要であれば教えてください。