Keep a Changelog 準拠の形式で、このコードベースから推測される変更履歴を日本語で作成しました。

CHANGELOG.md
=============
すべての重要な変更はここに記録します。  
フォーマットは「Keep a Changelog」を準拠しています。

Unreleased
----------
（未リリースの変更はここに記載してください）

[0.1.0] - 2026-03-27
-------------------
Added
- 基本パッケージ初期実装を追加（kabusys v0.1.0）
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージを __all__ で公開。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイル自動読み込み（プロジェクトルート検出：.git または pyproject.toml）を実装。
  - .env/.env.local の読み込み順序、OS 環境変数保護（protected set）、上書き制御をサポート。
  - 高度な .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
  - 環境変数必須チェックのユーティリティ（_require）および Settings クラス（J-Quants、kabu API、Slack、DB パス、環境種別・ログレベル検証など）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグに対応。
- AI 関連モジュールを追加（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントをバッチ評価。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST 相当）を calc_news_window で提供。
    - バッチ処理（最大20銘柄/チャンク）、記事数/文字数制限（記事数＝10、文字数＝3000）でトークン膨張に対応。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。失敗はスキップし処理継続（フェイルセーフ）。
    - レスポンスバリデーション（JSON 抽出、results 配列・code/score 検証、スコアのクリップ）を実装。
    - ai_scores テーブルへ冪等的に置換（DELETE → INSERT）し、部分失敗時に既存スコアを保護。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事フィルタ用キーワード一覧、最大記事数制限、OpenAI 呼び出しのリトライとフェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - DuckDB を用いた ma200_ratio 計算、マクロニュース抽出、market_regime テーブルへの冪等書き込みを実装。
    - モジュール間の結合を避けるため OpenAI 呼び出し実装を分離（news_nlp と共有しない）。
- Data（データ基盤）モジュールを追加（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar に基づく営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB 登録がない日や NULL 値に対しては曜日ベースのフォールバック（週末除外）を一貫して適用。
    - calendar_update_job により J-Quants から差分取得・バックフィル・健全性チェック（未来日付の異常検出）・冪等保存を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラス（取得数・保存数・品質問題・エラーの集約）を実装。has_errors / has_quality_errors 等のヘルパを提供。
    - テーブル存在チェック、最大日付取得などのユーティリティを実装。
    - pipeline モジュールの ETLResult を etl パッケージから再公開。
  - jquants_client インターフェース利用を前提とした差分取得・保存・品質チェック方針を実装（jquants_client は外部依存）。
- Research（分析）モジュールを追加（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR）、Liquidity（20日平均売買代金・出来高比率）、Value（PER, ROE）を DuckDB SQL で計算。
    - データ不足ハンドリング（必要行数未満で None を返す）やログ出力を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン対応、horizons 検証）を calc_forward_returns で実装。
    - IC（Spearman の ρ）計算（rank 関数を含む）、統計サマリー（count/mean/std/min/max/median）を実装。
  - 研究ユーティリティをパッケージ API として再エクスポート（research.__init__）。
- 内部ユーティリティ・設計方針
  - ルックアヘッドバイアス防止のため、いずれのスコア計算／ETL／AI 呼び出しでも datetime.today()/date.today() を勝手に参照しない設計（target_date を明示受け渡し）。
  - DuckDB を主な永続ストレージとして使用。SQL と Python を組み合わせて処理を実装。
  - OpenAI 呼び出し部分はテスト容易性のため差し替え可能（ユニットテストでモック可能）。

Changed
- （初版のため履歴は最初の機能追加に相当）

Fixed
- .env パーサでのクォート内部エスケープやインラインコメント処理、export プレフィックス対応など、現場でよくある形式に対応（設定読み込みの堅牢化）。

Security
- Settings はいくつかの鍵（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）を必須としていることを明示。自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を提供し、テスト/CI 時の誤漏洩リスクを低減。

Deprecated
- なし

Removed
- なし

Breaking Changes
- なし（初期リリース）

Notes / Implementation details
- OpenAI API 呼び出しは gpt-4o-mini を想定し、JSON Mode（response_format={"type": "json_object"}）での利用を前提としている。ただしレスポンスが完全な JSON でない場合の復元ロジックやバリデーションも実装済み。
- DuckDB バインドに起因する互換性（executemany に空リスト不可など）に配慮した実装を行っている。
- 外部 API クライアント（jquants_client, OpenAI）は実行環境で提供されることを前提とする。ユニットテストは各 _call_openai_api 等をモックしてテスト可能な設計。

もし特定の変更点をより詳しく（ファイル単位での差分やリリースノートの英文化など）記載したい場合は、どの観点を優先するか教えてください。