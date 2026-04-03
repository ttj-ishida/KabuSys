# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリース日付はコードベースの推定作成日を基に記載しています。

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-03
初回公開リリース。本バージョンは日本株自動売買プラットフォームのコアライブラリとして以下の機能群を実装しています。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` として設定。
  - パッケージ公開モジュール候補として data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（優先度: OS 環境変数 > .env.local > .env）。
  - .env パーサーはコメント、クォート、export 形式（export KEY=val）に対応。バックスラッシュエスケープやインラインコメントの扱いを考慮。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト時に使用可能）。
  - 必須キー未設定時に ValueError を送出する `_require` と、Settings クラス経由のプロパティアクセスを実装（J-Quants, kabuステーション, LINE, DB パス等）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL 等の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）を提供。

- AI 関連（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄毎のニュースを作成。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチ評価を実装（最大バッチサイズ 20 銘柄）。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列チェック、コード整合性、スコア数値チェック）。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE→INSERT のトランザクション）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能な内部フックを用意（_call_openai_api のパッチ可）。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - ユーティリティ: calc_news_window(target_date)

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei225 連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を参照し、OpenAI（gpt-4o-mini）によりマクロセンチメントを取得（記事なし時は LLM 呼出しを行わず 0.0 を使用）。
    - レスポンスの再試行/フォールバック（API失敗時 macro_sentiment=0.0）、JSON パース失敗時のフェイルセーフ。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データ管理（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar に基づく営業日判定 API（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
    - DB 登録値を優先し、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - calendar_update_job により J-Quants からの差分取得・バックフィル（直近数日）・健全性チェックを実装。
    - 最大探索日数の制限や不整合時の安全停止を実装。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を格納する dataclass `ETLResult` を実装（品質チェック結果・エラー情報等を含む）。
    - ETLResult は辞書化（to_dict）可能で監査ログに利用可能。
    - jquants_client を通じた差分取得・idempotent 保存・品質チェック連携を想定した設計（実処理は jquants_client / quality モジュールに依存）。
    - パイプライン用の公開型 ETLResult を etl モジュールで再エクスポート。

- Research / ファクター計算（kabusys.research）
  - ファクター計算群を実装（prices_daily / raw_financials を参照し外部 API にはアクセスしない方針）。
    - calc_momentum(conn, target_date): mom_1m/3m/6m と ma200_dev（200日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20日 ATR, ATR/price, 20日平均売買代金, 出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得して PER, ROE を算出。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons=None): 各ホライズンの将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算（有効レコード3件未満は None）。
    - factor_summary(records, columns): 各カラムの count/mean/std/min/max/median を計算。
    - rank(values): ランク計算（同順位は平均ランク、丸めによる誤差対策あり）。
  - 外部依存を最小化（pandas 等未使用）、標準ライブラリ + DuckDB のみで実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数で注入可能にし、環境変数直接依存を緩和（テスト・鍵管理の柔軟化）。
- .env の読み込みは OS 環境変数を保護する設計（デフォルトは既存 OS 環境変数を上書きしない）。.env.local は上書き可能。

### Notes / 実装上の注意点
- 全ての「日付を基準にした処理」は datetime.today() / date.today() を内部で直接参照しない設計（ルックアヘッドバイアスの防止）。外部から target_date を渡して検証可能にする。
- DuckDB を主要な分析 DB として想定。executemany に空リストを渡せない DuckDB の制約に対する対策が入っている（空リストチェック）。
- AI レスポンスは JSON Mode を利用しているが、余計な前後テキストが混入する場合の復元ロジックを組み込んでいる。
- API 呼び出しや DB 書込みはトランザクションで保護し、部分失敗時に既存データを不必要に消さない方針（コード単位で DELETE→INSERT）。
- テスト容易性のため、OpenAI 呼び出しをパッチ可能な内部関数でラップしている（ユニットテストで外部 API を差し替えられる）。

### Breaking Changes
- （初回リリースのため該当なし）

---

今後の予定（例）
- strategy / execution / monitoring の具体実装（現状はモジュール名のプレースホルダを定義済み）。
- jquants_client, quality モジュールとの統合テスト・運用監視強化。
- ドキュメント（API リファレンス・運用手順書）の拡充。

-------------------------
参考: 本 CHANGELOG はソースコード内の設計コメント・関数名・処理フローから推測して作成しています。実際のリリースノートは実装・コミット履歴に基づき適宜修正してください。