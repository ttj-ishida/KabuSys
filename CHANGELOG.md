# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0 - 初回リリース

<!--
  参考: Keep a Changelog のセクション
  - Added: 新機能
  - Changed: 既存機能の変更
  - Deprecated: 非推奨
  - Removed: 削除
  - Fixed: バグ修正
  - Security: セキュリティ修正
-->

## [Unreleased]

今後のリリース向けの保留中の変更はここに記載します。

---

## [0.1.0] - 2026-03-27

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な内容は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - モジュール群: data, research, ai, execution, strategy, monitoring を公開。

- 環境設定管理
  - .env ファイルと OS 環境変数を統合して読み込む自動ローダーを実装（src/kabusys/config.py）。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索し、CWD 非依存で動作。
    - 読み込み順序は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env パーサは export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - _load_env_file は既存 OS 環境変数の保護機能（protected）を持ち、override フラグで上書き制御。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境等の設定をプロパティ経由で取得（必須値未設定時は明確な例外を送出）。
  - 環境値検証（KABUSYS_ENV の有効値制限、LOG_LEVEL のバリデーション）を実装。

- AI（自然言語処理）モジュール
  - ニュースセンチメント分析 (score_news)
    - raw_news + news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別スコアを ai_scores テーブルへ保存（src/kabusys/ai/news_nlp.py）。
    - 設計上の特徴:
      - JST 時刻ウィンドウ（前日15:00〜当日08:30）を UTC に変換して厳格に処理（calc_news_window）。
      - 1チャンク最大 20 銘柄、1銘柄あたり最大記事数・最大文字数でトリム。
      - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。その他エラーはスキップして継続（フェイルセーフ）。
      - JSON Mode のレスポンスを堅牢にパースし、余分な前後テキストから最外側の {} を抽出する復元処理を実装。
      - スコアは ±1.0 にクリップ。部分失敗に備え、ai_scores は該当コードのみ DELETE → INSERT の置換を行う（冪等性確保）。
      - テスト容易性のため OpenAI 呼び出し関数を patch で差し替え可能（_call_openai_api）。
  - 市場レジーム判定 (score_regime)
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull / neutral / bear）を決定し market_regime テーブルへ保存（src/kabusys/ai/regime_detector.py）。
    - 設計上の特徴:
      - prices_daily の date < target_date の排他条件など、ルックアヘッドバイアス防止の取り扱いを徹底。
      - API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
      - OpenAI 呼び出しは独立実装でモジュール結合を避ける。最大リトライ・エクスポネンシャルバックオフを実装。

- リサーチ（ファクター計算・特徴量探索）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m と ma200_dev（200日MA乖離）を計算。
    - Volatility & Liquidity: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - Value: PER（EPSが0/欠損なら None）、ROE を raw_financials と prices_daily から計算。
    - DuckDB SQL を主体に実装し、結果を (date, code) キーの dict リストで返す。
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - forward returns（将来リターン）の計算（horizons デフォルト [1,5,21]）。
    - IC（Spearman の ρ）計算（rank による tie の平均化を考慮）。
    - factor_summary: count/mean/std/min/max/median を算出。
    - rank ユーティリティ（同順位は平均ランク）および zscore_normalize の再エクスポートを提供。

- データプラットフォーム（DuckDB ベース）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）のフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー集計など）。
    - 差分取得、バックフィル（日数制御）、品質チェックのポイントを設計に明示。
    - _get_max_date 等の DB ヘルパー実装。
  - ETL ユーティリティの公開インターフェースを提供（src/kabusys/data/etl.py）。

- 外部 API クライアント設計
  - jquants_client への参照を使った差分取得・保存処理を想定（実装ファイルは data パッケージ内で利用）。
  - OpenAI クライアント呼び出しは OpenAI SDK を利用（api_key を引数注入可能、テスト時は patch で差し替え可能）。

- 汎用設計方針・品質
  - ルックアヘッドバイアス防止: 主要なスコアリング処理で datetime.today()/date.today() を直接参照しない実装方針を徹底。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 等を想定）。トランザクション（BEGIN/COMMIT/ROLLBACK）で障害時に整合性を保護。
  - API 呼び出しの堅牢化（リトライ・バックオフ・エラーハンドリング）やレスポンス検証を多数実装。
  - 外部依存を抑え、標準ライブラリ + duckdb + OpenAI SDK を中心に設計（pandas 等に依存しない実装）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OPENAI_API_KEY 等の機密情報は明示的に引数または環境変数で取得。自動ロード時も OS 環境変数は保護され、.env の上書きは制御可能（protected set）。

---

開発者向けメモ（実装上の注意）
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動ロードを無効化できます。
- OpenAI 呼び出し部分はモックしやすいよう関数単位で分離しています（unittest.mock.patch を利用）。
- DuckDB の executemany で空リストを渡せない制約に配慮した実装箇所があります（部分置換ロジック）。
- 将来の拡張点として、kabu ステーションとの連携・発注ロジックや、監視/モニタリング用テーブルの実装が想定されています。

---

（補足）今後のリリースでは以下が想定されます（未実装機能・改善候補）
- 発注実行モジュール（kabu API 経由）の実装とテスト
- 監視・アラート（Slack 連携）ロジックの強化
- ETL の並列化・パフォーマンス改善、品質チェックルールの拡充
- ai モジュールの追加評価指標やプロンプト改善

以上。