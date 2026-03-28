# Keep a Changelog
すべての主な変更点をここに記録します。  
このプロジェクトでは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従います。

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
- 基本パッケージ構成を追加:
  - kabusys.__init__ にバージョン情報と主要サブパッケージの公開設定を追加。
- 環境設定管理:
  - kabusys.config:
    - .env / .env.local の自動読み込み機能（プロジェクトルート自動検出: .git または pyproject.toml）。
    - 複雑な .env パース実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数サポート。
    - 必須環境変数チェック(_require) と Settings クラスを提供（J-Quants, kabu, Slack, DB パス, 実行環境等）。
    - KABUSYS_ENV / LOG_LEVEL の検証ロジック（有効値チェック）。
- AI 関連機能:
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する score_news 関数を実装。
    - タイムウィンドウ計算（JST 前日15:00～当日08:30 相当の UTC 変換）を提供（calc_news_window）。
    - バッチ処理、1 チャンクあたり最大銘柄数、文字数・記事数トリム等のトークン肥大化対策。
    - JSON Mode レスポンスの堅牢なパースとバリデーション（出力整合性・数値チェック・スコアクリップ）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライとフェイルセーフ（失敗時は対象銘柄をスキップして継続）。
  - kabusys.ai.regime_detector:
    - ETF 1321（日経225連動）の200日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを重み合成して市場レジーム（bull/neutral/bear）を日単位で判定する score_regime を実装。
    - マクロニュース抽出（キーワードベース）・OpenAI 呼び出し・再試行ロジック・合成スコアのクリップ・冪等な DB 書き込みを実装。
    - API失敗時には macro_sentiment=0.0 をフォールバックするフェイルセーフ設計。
    - モジュール間の結合を低く保つため、OpenAI 呼び出しは news_nlp と別実装に分離。
- データプラットフォーム関連:
  - kabusys.data.pipeline / kabusys.data.etl:
    - ETL パイプラインの基礎（差分取得、保存、品質チェック）を実装するためのインターフェース。
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー集約・シリアライズ機能）。
  - kabusys.data.calendar_management:
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB が未取得のときは曜日ベースでフォールバックする堅牢なロジック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存フローを実装。
  - kabusys.data パッケージの ETLResult 再エクスポート。
- リサーチ／因子解析:
  - kabusys.research パッケージに因子・特徴量解析機能を追加:
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、ma200 乖離等のモメンタムファクターを算出（DuckDB SQL ベース）。
      - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率等を算出。
      - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - feature_exploration:
      - calc_forward_returns: 各ホライズンの将来リターンを一括で取得する効率的クエリ。
      - calc_ic: スピアマンランク相関（IC）計算（欠損・定数系列時のガードあり）。
      - rank: 同順位は平均ランクで扱うランク化ユーティリティ。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - 研究用ユーティリティとして kabusys.data.stats.zscore_normalize を再利用できる公開インターフェースを提供（research.__init__ にエクスポート）。
- DuckDB との統合設計:
  - 多くの処理は DuckDB 接続を受け取り SQL と Python を組み合わせて実行する設計（外部 API 呼び出しを伴わない分析・バックテスト向け）。
  - DB 操作は明示的な BEGIN / DELETE / INSERT / COMMIT を使い、失敗時には ROLLBACK を試みる冪等性と整合性を重視。
- テスト容易性/拡張性:
  - OpenAI 呼び出しをテスト時に差し替え可能（_call_openai_api を patch して置き換えられる設計）。
  - 設定や API キーは関数引数から注入可能（api_key 引数がある関数）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Known issues / Notes
- OpenAI API キー（環境変数 OPENAI_API_KEY または各関数の api_key 引数）が未設定だと score_news / score_regime は ValueError を送出します。運用環境では適切な API キーの設定が必要です。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、該当箇所で空チェックを行う実装になっています。
- .env 自動ロードはプロジェクトルートの検出に基づくため、配布後やインストール形態によっては自動ロードを無効化して明示的に環境を設定することを推奨します（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 外部モジュール（jquants_client, quality など）の実装に依存しており、それらの実装や API の変更が影響します。

Security
- API キー等の機密情報は .env / 環境変数で管理する設計。リポジトリにハードコードしないこと。

将来の TODO（主な拡張候補）
- PBR・配当利回りなど Value ファクターの拡張。
- AI モデル選択・プロンプト改善やレスポンスフォーマットの厳格化。
- ETL のジョブ化・スケジューリングユーティリティの追加。
- 単体テスト・統合テストの追加（現在はテスト支援フックを用意）。

---  
この CHANGELOG はソースコードの実装内容と docstring / コメントから推測して作成しています。追加の変更点や実運用上の注意事項があれば適宜追記してください。