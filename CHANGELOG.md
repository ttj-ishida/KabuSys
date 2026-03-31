# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、本CHANGELOGは提供されたソースコードから実装済み機能・設計意図・既知制約を推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-31

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - 公開モジュール: data, strategy, execution, monitoring

- 環境設定・自動 .env ロード機能を追加（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から探索し、.env / .env.local を自動読込
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）
  - .env のパースは export 形式、クォート、エスケープ、行内コメント処理を考慮
  - .env.local は .env の上書きとして優先適用（ただし OS 環境変数で保護）
  - Settings クラスを提供し、必須変数取得（_require）や既定値、型チェックを行う:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須取得
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH などに既定値
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の値検証
    - is_live / is_paper / is_dev の補助プロパティ

- AI（自然言語処理）モジュールを追加（src/kabusys/ai）
  - news_nlp.score_news: ニュース記事の銘柄別センチメントを OpenAI（gpt-4o-mini）で評価し ai_scores に書き込み
    - ニュース取得ウィンドウは JST 前日 15:00 ～ 当日 08:30（内部は UTC naive に変換）
    - 1銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - 1回の API コールで最大 20 銘柄をバッチ処理（_BATCH_SIZE）
    - JSON モードを利用し、応答のバリデーション（results 配列・code・score チェック）を実装
    - レスポンス不正や API エラーは個別チャンクをスキップして処理を継続（フォールセーフ）
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（最大リトライ回数設定）
    - DuckDB 互換性のため executemany に空リストを渡さない等の対処
    - テスト容易性のため API 呼び出し関数をパッチ差替え可能（kabusys.ai.news_nlp._call_openai_api）

  - regime_detector.score_regime: マクロ＋テクニカルを合成した市場レジーム判定（bull/neutral/bear）を market_regime に書き込み
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成
    - ma200_ratio は target_date 未満のデータのみを使用しルックアヘッドを防止
    - マクロ記事は指定キーワードでフィルタ（_MACRO_KEYWORDS、最大記事数制限）
    - OpenAI 呼び出しは独立実装でテスト差替え可能（kabusys.ai.regime_detector._call_openai_api）
    - API失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - DB へは冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、例外発生時に ROLLBACK を試行

- Research モジュールを追加（src/kabusys/research）
  - factor_research.Calculate:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（prices_daily）
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等（prices_daily）
    - calc_value: PER / ROE を raw_financials と prices_daily から結合して計算（最新財務データを target_date 以前から取得）
    - 設定として営業日ベース / スキャン範囲バッファや不足データ時の None 処理を実装
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括取得
    - calc_ic: スピアマン（ランク相関）による IC 計算（rank ユーティリティと結合）
    - factor_summary: 各ファクターカラムの count/mean/std/min/max/median を算出
    - rank: 同順位は平均ランクを返す実装（小数丸めによる ties 対応）
  - zscore_normalize を data.stats から再エクスポート（研究ユーティリティ連携）

- Data プラットフォーム用ユーティリティを追加（src/kabusys/data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定／next/prev/get_trading_days/is_sq_day を実装
    - DB 登録がない日や NULL 値は曜日ベース（週末除外）でフォールバックする一貫したロジック
    - 夜間バッチ calendar_update_job: J-Quants API から差分取得し冪等保存、バックフィル・健全性チェックあり
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.ETLResult として再エクスポート）
    - ETL パイプライン設計（差分取得、保存、品質チェックの方針をコードドキュメント化）
    - _get_max_date / _table_exists 等の内部ユーティリティを実装

Changed
- 新規リリースのため変更履歴なし（初期導入）

Fixed
- なし（初期導入）

Security
- なし（初期導入）

Notes / 既知の制約・設計上の注意
- OpenAI API のキーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。
- LLM に依存する機能（news_nlp / regime_detector）は API 呼び出し失敗時に中立値（0.0）やスキップで継続する設計（フェイルセーフ）。ただし品質や完全性は保証されないため監視が必要。
- 時刻取り扱い:
  - ニュースウィンドウ等は JST をベースに UTC naive datetime を返す（DB の raw_news.datetime は UTC で保存されている前提）。
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を内部ロジックで参照しない方針（target_date を明示的に与える）。
- DuckDB 互換性対応:
  - executemany に空リストを渡さない等の実装上の注意点がある（DuckDB 0.10 の制約に対応）。
- DB 書き込みはできるだけ冪等に実装（DELETE → INSERT など）して部分失敗時の既存データ保護を考慮。
- テスト容易化:
  - 内部の OpenAI 呼び出しはパッチ差し替え可能（ユニットテストで差し替えて API をモック可能）。
  - 環境ファイル自動ロードは無効化可能。

今後の TODO（推測）
- data.jquants_client の詳細実装・テスト
- strategy / execution / monitoring モジュールの具現化（エントラスト・注文発行・監視）
- 単体テスト・統合テストの追加（特に OpenAI 絡みのリトライ・パースロジック）
- ドキュメント（API 仕様・運用手順・環境変数一覧）の整備

---

参考: この CHANGELOG は提供されたソースコードから観察できる機能・設計方針に基づいて作成しています。追加のコミット履歴や設計ノートがある場合は差分を反映して更新してください。