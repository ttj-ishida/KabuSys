# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点・設計方針・安全対策は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名・バージョン設定（0.1.0）、公開サブパッケージを __all__ で定義（data, strategy, execution, monitoring）。
- 設定管理
  - src/kabusys/config.py:
    - .env および .env.local、OS 環境変数からの設定自動ロード機能を実装。
    - .env ファイルのパース機能（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱い）を実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル判定などのプロパティを提供。
    - 必須環境変数未設定時は ValueError を送出する _require を提供。
- AI モジュール
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事から銘柄別センチメント（ai_score）を生成し ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ計算（JST → UTC 変換）、記事集約（銘柄ごとに最新記事を制限）、トークン肥大化対策（記事数・文字数のトリム）、バッチ送信（最大20銘柄）、OpenAI JSON Mode のレスポンスバリデーション・抽出、スコアのクリップ、DuckDB への冪等書き込み（DELETE→INSERT）を実装。
    - API リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフをサポート。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - テスト置換可能な _call_openai_api のラッパーを実装。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算・保存する処理を実装。
    - prices_daily / raw_news / market_regime テーブルを参照し、冪等的に market_regime を更新（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しのリトライ・エラー処理（フェイルセーフで macro_sentiment=0.0 にフォールバック）を実装。
    - LLM のレスポンス JSON パースやステータスコードに応じたロジックを実装。
- Research モジュール
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）ファクター計算関数を実装。DuckDB の SQL ウィンドウ関数を活用して効率的に算出。
    - 欠損・データ不足時の扱い（None を返す）やログ出力を考慮。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク関数（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存を使わず標準ライブラリ＋DuckDB ベースで実装。
  - src/kabusys/research/__init__.py: 上記関数を再エクスポート。
- Data モジュール
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダーの管理（market_calendar テーブル）、営業日判定（is_trading_day/is_sq_day）、前後の営業日取得（next_trading_day/prev_trading_day）、期間内営業日取得（get_trading_days）を実装。
    - market_calendar が未取得時の曜日ベースのフォールバック、DB 優先の一貫した判定ロジックを提供。最大探索日数やバックフィル、健全性チェックを導入。
    - calendar_update_job により J-Quants からの差分取得と冪等保存を実装（fetch/save は jquants_client を利用）。
  - src/kabusys/data/pipeline.py:
    - ETL パイプラインの基礎（差分取得、保存、品質チェックの呼び出し、バックフィル戦略）を実装。_get_max_date 等のユーティリティを提供。
    - ETLResult データクラス（src/kabusys/data/pipeline.py 内）を実装し、取得/保存件数・品質問題・エラー情報を集約。to_dict により品質問題をシリアライズ可能。
  - src/kabusys/data/etl.py: ETLResult の再エクスポート。
  - jquants_client（参照）：外部クライアントモジュールを利用する想定（fetch/save 関数呼び出し箇所あり）。
- Logger/設計上の注意点
  - ルックアヘッドバイアス対策: date.today()/datetime.today() を判定ロジックの基準に直接使わない設計（target_date を明示的に受け取る関数群）。
  - DuckDB を主要なローカルデータストアとして利用。
  - OpenAI（gpt-4o-mini）を利用した JSON Mode 呼び出し、レスポンスの堅牢なパース・検証処理を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数パーサの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、上書き制御（protected set）などに対応。
- OpenAI レスポンス解析の堅牢化
  - JSON mode でも前後に余計なテキストが混入した場合に最外の波括弧を抜き出して復元を試みるフォールバック実装。
  - 非 5xx エラーや JSON パース失敗時は例外を投げず警告ログを出して安全側のデフォルト（0.0 やスキップ）で継続。

### Security
- 機密情報（OpenAI API キー、J-Quants トークン、Kabu API パスワード、Slack トークン等）は環境変数で管理する設計。Settings は未設定時に明確なエラーを発生させるため、運用時に必須設定の漏れを早期に検出可能。

### Notes / Known limitations
- 依存:
  - DuckDB、openai（OpenAI Python SDK）、および jquants_client（プロジェクト側の実装）が必要。
- OpenAI の利用に際してはレスポンス形式・利用料・レート制限に注意してください。ライブラリ側ではリトライ/バックオフを実装していますが、運用ポリシーに合わせた追加対策（レート監視・バッチ調整等）を推奨します。
- Slack / kabu ステーション / J-Quants との連携部分は設定値と外部クライアントに依存します。接続や権限管理は導入時に環境に応じて設定してください。
- strategy / execution / monitoring パッケージは __all__ に含まれていますが、このリリースでは内部実装が揃っていない、あるいは別モジュールで提供される想定があります。運用前に各サブパッケージの実装状況を確認してください。

---

作業の方針・設計に関する補足（要約）
- すべてのデータ取得・スコア計算は明示的な target_date を用いる（ルックアヘッド防止）。
- API 関連はフェイルセーフ（部分失敗で全体停止しない）、冪等性（DB 書き込み）を重視。
- DuckDB を中心としたオンプレミス／ローカル分析に最適化した設計。