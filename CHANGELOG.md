# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」コアライブラリの基盤機能群を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ初期化
  - パッケージバージョン管理と公開モジュールを設定（kabusys/__init__.py）。

- 設定管理（kabusys.config）
  - .env および .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env 行パーサを実装し、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - 環境変数保護（既存 OS 環境変数を上書きしない / .env.local で上書き可能）をサポート。
  - 必須項目チェック関数 _require と Settings クラスを提供。J-Quants / kabuステーション / Slack / データベース / 実行環境設定をプロパティ経由で取得。
  - 環境値の検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の有効値チェック。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を利用して銘柄別センチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティを提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、記事トリム（件数・文字数制限）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 保護（対象コードのみ DELETE → INSERT）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライとフェイルセーフ（最終的にスキップして継続）。
    - LLM レスポンスの JSON 抽出（前後余分テキストが混ざるケースに対処）と堅牢なバリデーションロジック実装。
    - テスト容易性のため API 呼び出しラッパーを分離しモック可能に実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出（キーワードリストベース）、OpenAI 呼び出し（gpt-4o-mini）によるセンチメント評価、スコア合成、regime テーブルへの冪等書き込みを実装。
    - API リトライ、エラー時のデフォルト macro_sentiment=0.0（フェイルセーフ）、およびルックアヘッドバイアス防止のクエリ設計を採用。
    - API キー注入可能（引数または環境変数 OPENAI_API_KEY）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定 / 次・前営業日取得 / 期間内営業日列挙 / SQ 判定のロジックを実装。
    - DB データがない場合は曜日ベース（土日除外）でフォールバック。DB が部分的にしかない場合も一貫した判定を保証。
    - 夜間バッチ更新ジョブ（calendar_update_job）で J-Quants から差分取得→冪等保存（ON CONFLICT 相当）を行う仕組みを実装。バックフィルと健全性チェックを実装。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL の結果を表す ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分更新、バックフィル、J-Quants クライアント経由での idempotent 保存、品質チェック（quality モジュールと連携）を想定した設計。エラー収集と部分失敗保護の方針を採用。
    - DuckDB を前提とした最大日取得やテーブル存在チェック等のユーティリティを実装。

  - jquants_client との連携を前提としたデータ取得/保存ワークフロー（クライアントに依存する箇所は例外処理を含め保護）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Liquidity（20 日平均売買代金・出来高比率）、Value（PER、ROE）等のファクター計算関数を実装。
    - DuckDB に対する SQL ベースの実装で、データ不足時の None 戻しなど堅牢な振る舞いを実現。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearmanランク相関）計算、ファクター統計サマリー、ランク付けユーティリティを提供。
    - pandas 等に依存せず標準ライブラリのみで実装。入力検証と欠損値/非有限値の扱いに注意を払った設計。

- 共通設計方針（全体）
  - ルックアヘッドバイアス対策の徹底（datetime.today()/date.today() を直接参照しない関数設計）。
  - DuckDB を想定した互換性対応（executemany の空リスト回避等）。
  - DB 書き込みは冪等性を考慮（DELETE→INSERT パターンや BEGIN/COMMIT/ROLLBACK を活用）。
  - OpenAI API 呼び出し周りはリトライ・バックオフ、レスポンスパースの堅牢化、API キー注入でテスト容易性を確保。

### Fixed
- （初版のため該当なし）

### Changed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

---

開発・運用に関する注意点:
- OpenAI の API キーを利用する機能（news_nlp, regime_detector）は api_key 引数で注入可能ですが、未指定時は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。
- .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能です（テスト用）。
- DuckDB テーブルスキーマや外部 jquants_client の実装が前提となる箇所があります。実運用前にスキーマ整備・外部クライアント実装を確認してください。

貢献者: 初回実装（コア機能群の作成）