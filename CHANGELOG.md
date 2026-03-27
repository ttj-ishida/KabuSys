# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。主な追加点は以下の通りです。

### 追加（Added）
- パッケージ公開
  - パッケージルート: kabusys（__version__ = 0.1.0）
  - 公開モジュール群: data, strategy, execution, monitoring

- 環境設定／起動周り（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を自動読み込み
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
    - OS 環境変数を保護する protected オプションを実装（.env.local の上書き挙動制御）
  - 高度な .env パーサ実装
    - export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理
  - Settings クラスを追加（settings インスタンスをエクスポート）
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティ提供
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ロジック
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供
      - DB 登録値優先、未登録日は曜日ベースでフォールバック
      - 最大探索日数制限により無限ループ防止
    - 夜間バッチ更新 job: calendar_update_job
      - J-Quants からカレンダーを差分取得して冪等保存（バックフィル・健全性チェック含む）
  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを公開（etl.ETLResult を kabusys.data.etl で再エクスポート）
    - 差分更新、バックフィル、品質チェックの設計を反映したユーティリティ関数群
    - DuckDB を前提としたテーブル存在チェックや最大日付取得などのヘルパ関数

- 研究／ファクター（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を計算
    - calc_volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率を計算
    - calc_value: raw_financials から PER, ROE を計算（target_date 以前の最新財務を使用）
    - 設計上、DuckDB の prices_daily / raw_financials のみ参照し実環境の注文等にはアクセスしない
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算
    - calc_ic: スピアマンランク相関（IC）の計算（コード結合・欠損除外・最小サンプルチェック）
    - rank: 平均ランク（同順位は平均ランク）への変換ユーティリティ
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ

  - 研究用ユーティリティの再エクスポート
    - kabusys.data.stats.zscore_normalize を再エクスポート

- AI / ニュース（kabusys.ai）
  - news_nlp モジュール
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores に書き込み
    - バッチ処理（最大 20 銘柄／コール）、1 銘柄あたり記事トリム（最大記事数・文字数制限）
    - JSON Mode を想定したレスポンスバリデーションとスコアの ±1.0 クリップ
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx）、指数バックオフ
    - API 失敗時は該当チャンクをスキップして他チャンクの処理を継続（フェイルセーフ）
    - calc_news_window: JST 基準のニュース収集ウィンドウ計算（UTC naive datetime を返す）
    - テスト容易性: _call_openai_api をパッチ差し替え可能
  - regime_detector モジュール
    - score_regime: ETF コード 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し market_regime に書き込み
    - マクロニュース選別（キーワード群）と LLM スコアリング（モデル gpt-4o-mini）、API リトライ／エラーハンドリング実装
    - レジームスコアのクリッピングとラベリング（bull / neutral / bear）
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック保護

### 改善（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### セキュリティ（Security）
- （既知のセキュリティ対応事項はなし）

### 備考（Notes / 実装上の設計判断）
- ルックアヘッドバイアス回避のため、内部実装は datetime.today() / date.today() をコアロジックで参照しない方向で設計されています（target_date を明示的に渡す方式）。
- OpenAI 等外部 API への呼び出しは堅牢化（リトライ・バックオフ・タイムアウト・パース失敗フォールバック）されており、API 障害時は中立スコア（0.0）やチャンクスキップで継続します。
- DuckDB を前提にした実装で、書き込みは可能な限り冪等性（DELETE → INSERT 等）を保つようにしています。
- テスト性を高めるため、OpenAI 呼び出しや内部時刻計算などはパッチ差し替え（mock）しやすい構造になっています。

---

今後のリリースでは、戦略（strategy）と発注（execution）、及びモニタリング（monitoring）周りの機能実装・精緻化、運用上の設定拡張や性能改善（ETL の並列化等）を予定しています。