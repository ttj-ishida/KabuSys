Changelog
=========

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-04-09
------------------

Added
- 初回リリース: kabusys パッケージを追加。
  - パッケージ概要: 日本株自動売買システムのコアライブラリ（モジュール構成: data, research, ai, monitoring, strategy, execution 等を想定）。
- 環境設定/ロード機能（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を参照）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント処理など）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを追加し、J-Quants / kabuAPI / LINE / DB / Paper Trading / 監視 / ログ等の設定プロパティを公開。
  - 設定値のバリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL などの許容値チェック）。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores テーブル）を生成・上書きする処理を実装。
    - チャンク処理（最大20銘柄／チャンク）、1銘柄あたり記事数上限・文字数トリム、JSON Mode の結果バリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。失敗時は部分的にスキップして継続するフェイルセーフ設計。
    - calc_news_window により JST ベースのニュースウィンドウ（前日15:00〜当日08:30 JST）を UTC に変換して扱う。
  - regime_detector.score_regime:
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書込。
    - マクロニュース抽出（キーワード一覧）→ LLM スコア化（gpt-4o-mini）→ 合成スコア計算のフローを実装。
    - API 障害時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
  - AI 呼び出しは JSON レスポンスの厳格検証を行い、パース失敗時にログを出すことで安全にスキップする実装。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar）と関連ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータが無い場合は曜日ベース（週末は休場）でフォールバックする一貫した設計。
    - calendar_update_job により J-Quants から差分取得・バックフィル・健全性チェックを行い冪等的に保存する処理を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー等を集約）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装。（詳細ロジックは jquants_client / quality モジュールと連携）
  - etl モジュールは ETLResult を再エクスポート。
  - jquants_client を用いた外部 API 連携箇所を想定した設計。
- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（prices_daily を利用）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算。
    - すべて DuckDB を用いた SQL ベースでの実装、外部 API 参照は無し。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得（ホライズンは検証と制限あり）。
    - calc_ic: スピアマン順位相関（IC）を実装。データ不足時は None を返す。
    - rank / factor_summary: ランク付け（平均順位による同順位処理）と基本統計量サマリーを実装。
  - research.__init__ で主要関数を再エクスポート。
- 基盤的な実装方針（横断）
  - DuckDB を主要なローカル分析ストアとして利用。
  - すべての「日付基準」処理（AI スコア / ファクター計算 / ETL 等）は datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取ることでルックアヘッドバイアスを防止。
  - DB 書き込みは冪等性を意識（BEGIN / DELETE / INSERT / COMMIT など、部分失敗時の保護ロジック）。
  - ロギング（情報・警告・例外）を多用して運用時の観測性を確保。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を使用して解決。未設定時は ValueError を投げて明示的に扱う設計（誤用を防止）。

Notes / Implementation details
- OpenAI 呼び出しは各モジュールで専用の _call_openai_api を持ち、モジュール間でプライベート関数を共有しないことで結合度を下げている。
- API 呼び出しのリトライは RateLimitError / APIConnectionError / APITimeoutError / 5xx を対象に指数バックオフを実施。その他のエラーはログを残してスキップすることで長期バッチ処理の堅牢性を向上。
- DuckDB の executemany に関する互換性（空リスト不可など）を考慮した防御的実装がある。

Contributors
- コードベースの実装を基に Changelog を作成。

---

注: 本 CHANGELOG は提供されたソースコードから機能と設計方針を推測して作成しています。実際のリリースノート作成時はリリース日・著者情報・依存関係の固定バージョンなどを合わせて記載してください。