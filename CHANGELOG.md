CHANGELOG
=========

すべての注目すべき変更をここに記録します。  
このファイルは「Keep a Changelog」規約に準拠しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-27
--------------------

Added
- 初回リリース。日本株自動売買/リサーチ/データプラットフォームの基本機能を実装。
- パッケージ公開情報
  - kabusys.__version__ = "0.1.0"
  - パブリック API: kabusys.data, kabusys.research, kabusys.ai など主要サブパッケージをエクスポート。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - セーフな .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 必須設定取得用の _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーションを実装。is_live/is_paper/is_dev のヘルパを追加。
  - データベースのデフォルトパス（DUCKDB_PATH, SQLITE_PATH）の取り扱い（Pathとして展開）。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して比較）。
    - バッチ処理: 最大20銘柄単位で API コール、1 銘柄あたり記事上限・文字数上限でトリム。
    - 再試行戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ／リトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code と score の検証、既知コードのみ有効化、スコアクリップ）。
    - DB 書き込みは部分失敗耐性あり（対象コードだけ DELETE→INSERT することで既存データを保護）。
    - テスト用に _call_openai_api を差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロ記事はキーワードフィルタで抽出（日本・米国関連ワードを事前定義）。
    - OpenAI 呼び出しは専用のロジックで実装、再試行とフォールバック（API 失敗時は macro_sentiment=0.0）。
    - レジーム判定結果は market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止の設計（date < target_date 等の厳格な条件、datetime.today() を直接参照しない）。

- データモジュール (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar に基づく営業日判定・次/前営業日取得・期間内営業日取得・SQ日判定を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック（週末除外）。
    - 最大探索幅で無限ループを防止し、健全性チェック・バックフィルをサポート。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（バックフィル期間あり、API エラー時は安全に中断）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー収集など）。
    - 差分取得、backfill、品質チェック（quality モジュール利用）を想定した実装の土台を提供。
    - jquants_client を利用した保存処理の呼び出しと結果集計設計。

- Research（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン・200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB ベースで計算する関数群を実装。
    - データ不足時の扱い（必要日数未満なら None を返す）や過去データスキャン範囲のバッファ設計を盛り込む。
  - feature_exploration
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（スピアマンの順位相関）計算、ランク変換、統計サマリーを実装。
    - pandas 等に依存せず、標準ライブラリで完結する実装。
  - research パッケージ __all__ で主要関数を再エクスポート。

Changed
- なし（初回リリースのため過去バージョンからの変更なし）。

Fixed
- なし（初回リリースのため過去バージョンからの修正なし）。

Notes / 実装上の注意点（ドキュメント的記載）
- OpenAI 連携
  - API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。
  - gpt-4o-mini + JSON Mode を前提に実装。API レスポンスの頑健なパースとフォールバックを実装済み。
- 時間/データ参照の安全性
  - ルックアヘッドバイアスを避けるため、モジュール内で datetime.today()/date.today() を直接参照しない設計（多くの関数で target_date を明示的に受け取る）。
- トランザクションと冪等性
  - DBへの書き込みは BEGIN/COMMIT/ROLLBACK を用いた明示的トランザクションで行い、既存レコードを対象日・コード単位で削除→挿入することで冪等性を担保。
- フォールバック動作
  - API失敗やデータ不足時は「継続（safe-fail）」の挙動を優先（例: macro_sentiment=0.0、スコア未取得コードは無視、該当テーブル更新をスキップなど）。
- テストのしやすさ
  - OpenAI 呼び出しや .env ロードなどは差し替え可能（モック可能）な設計を意識。

開発者向け TODO / 既知の制限
- PBR・配当利回りなどバリュー指標は未実装（calc_value に注記あり）。
- calendar_update_job / pipeline の外部呼び出し（jquants_client, quality モジュール）については実行環境依存。実稼働前に API クレデンシャルと DB スキーマの準備が必要。
- DuckDB バインドの挙動差異（executemany の空リスト等）に対する互換性処理を実装済みだが、利用する DuckDB のバージョンでの検証を推奨。

訳注
- 本 CHANGELOG は提示されたコードベースの実装内容から推測して作成しています。実際のリリースノートは運用上の決定（リリース日付、追加・削除された機能、バージョン方針）に基づき調整してください。