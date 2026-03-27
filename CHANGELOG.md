Keep a Changelog
=================
すべての重要な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- なし

0.1.0 - 2026-03-27
------------------
初回リリース。以下の主要機能・設計方針・実装を含みます。

Added
- パッケージ初期化
  - kabusys パッケージを導入。__version__ = 0.1.0。
  - 公開 API: data, strategy, execution, monitoring（__all__）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを独自実装（export 形式・クォート・エスケープ・インラインコメント対応）。
  - OS 環境変数を保護する protected 機能（.env.local が .env をオーバーライドする挙動を制御）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の取得をプロパティで提供。
  - 必須環境変数未設定時は明示的に ValueError を送出する検査ロジックを導入。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。

- データプラットフォーム / ETL (kabusys.data.pipeline, etl, etl result)
  - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化。
  - 差分取得・バックフィル・品質チェックのためのユーティリティを実装（最終取得日の取得など、DuckDB 互換の実装を含む）。
  - DuckDB と連携するための互換性配慮（NULL / 日付変換等）。

- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダーを扱うためのユーティリティ群を実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - market_calendar テーブル存在時は DB 値を優先、未登録日は曜日ベースのフォールバック（週末判定）を行う一貫した挙動。
  - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新。バックフィル・健全性チェックを実装。
  - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止。

- 研究用分析モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム (1M/3M/6M リターン)、200日移動平均乖離、20日 ATR、20日平均売買代金・出来高等を計算する関数を提供。
    - DuckDB 上で SQL を使い再現可能に実装。
    - データ不足時の挙動（必要行数未満は None を返す）を明確化。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン calc_forward_returns（任意の営業日ホライズン対応）。
    - IC (Information Coefficient) をランク相関（Spearman）で計算する calc_ic。
    - factor_summary による基本統計量集計。
    - ランク関数 rank（同順位は平均ランク）を提供。
  - zscore_normalize を外部モジュールから再エクスポート。

- AI ベースのニュース解析 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとの記事を作成し、OpenAI（gpt-4o-mini, JSON Mode）へ送信してセンチメントを算出。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して DB クエリを行う calc_news_window を提供。
    - 銘柄ごとに記事をトリム（最大記事数・最大文字数）してトークン肥大化に対策。
    - 1チャンク最大 20 銘柄のバッチ処理、レスポンス検証・クリッピング（±1.0）、部分失敗時の DB 保護（対象 code のみ DELETE → INSERT）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ制御、その他はスキップしてフェイルセーフで継続。
    - JSON パースの堅牢化（前後の余計なテキストが混じるケースに対して最外の {} を抽出する復元処理）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事の抽出、LLM 呼び出し（gpt-4o-mini, JSON Mode）、スコア合成、market_regime への冪等書き込みを実装。
    - API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ設計。
    - 外部モジュール結合を避けるため OpenAI 呼び出し関数はモジュールごとに独立実装。
    - ルックアヘッドバイアス防止の設計（date 比較は target_date 未満や明示的ウィンドウを使用、datetime.today() を参照しない）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を利用する方式。未設定時は ValueError を送出し明示化。
- .env 自動読み込みは必要に応じて明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / 設計上の重要事項
- ルックアヘッドバイアス対策: AI 評価・ファクター計算・ニュースウィンドウ等はすべて target_date を基準とし、内部で datetime.today()/date.today() を参照しない実装方針を徹底。
- DB 書き込みは冪等性を重視（DELETE → INSERT のパターン、BEGIN/COMMIT/ROLLBACK の利用）。
- DuckDB のバージョン互換性に配慮（executemany の空リスト回避など）。
- LLM 呼び出しは JSON Mode を利用し、レスポンスの堅牢なバリデーションを行う。API エラーは基本的にリトライまたはスキップでフェイルセーフを担保。
- 一部モジュール（jquants_client, quality など）は外部クライアント/モジュールに依存しており、実運用では対応する実装/認証情報が必要。

Acknowledgements / TODO
- monitoring / strategy / execution の実装はパッケージエントリに含まれるが、本リリースでは詳細実装の有無に注意（外部参照や将来的拡張を想定）。
- 今後の作業:
  - 単体テスト・統合テストの追加（特に OpenAI 呼び出し箇所はモック化しやすい設計）。
  - ドキュメント（API 仕様、運用手順、環境変数サンプル .env.example）の整備。
  - 監視・アラート（Slack 通知等）連携の具体実装。