CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
リリース日はリポジトリ内の __version__（0.1.0）と現在日付を基準にしています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ修正

[Unreleased]
-------------

（次版に向けた未リリースの変更はここに記載します）

[0.1.0] - 2026-04-01
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルや環境変数から設定を読み込む自動ロード機能を実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を起点に探索。
  - エスケープ・クォート・インラインコメント等を考慮した .env パーサを実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require を提供。
  - アプリ設定 Settings クラスを公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK 等の getter、DB パスや監視閾値、環境判定ユーティリティを含む）。
- AI モジュール（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - チャンク処理（最大バッチサイズ 20 銘柄）、1 銘柄あたりの記事数・文字数上限、JSON Mode レスポンス検証、スコアのクリップ、部分成功時の DB 書き換え（DELETE → INSERT）ロジックを実装。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフとリトライを実装。
    - テスト向けに OpenAI 呼び出しを差し替え可能（_call_openai_api をモック可能）。
    - 公開関数: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei-linked ETF）の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止。
    - OpenAI 呼び出しは独立した実装で、API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフを備える。
    - 公開関数: score_regime(conn, target_date, api_key=None)
- データプラットフォーム関連（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を基にした営業日判定ユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先・未登録日は曜日ベースでのフォールバック、一貫した探索ロジック、最大探索範囲制限を実装。
    - JPX カレンダーを J-Quants から差分取得して冪等的に保存する夜間バッチ（calendar_update_job）を実装。バックフィルと健全性チェックあり。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装して ETL の集計結果（取得数・保存数・品質問題・エラー）を扱えるようにした。ETLResult は etl モジュールを通じて再エクスポートされる。
    - 差分取得、idempotent 保存（jquants_client の save_* を想定）、品質チェック統合の設計（品質問題は収集して呼び出し元に委ねる方式）。
- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR, 相対 ATR）、Value（PER, ROE）などのファクター計算を SQL + Python で実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照。
    - 欠損やデータ不足時の挙動（None を返す）を明確に実装。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient = Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas に依存せず標準ライブラリのみで実装。
  - research パッケージ __init__ から主要関数群を再エクスポート。
- 監査・設計上の注意点をドキュメント化
  - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない方針を各 AI/Research モジュールで採用。
  - OpenAI API 呼び出しに対するモックポイントを用意してユニットテストしやすい設計。
  - DuckDB をデータ層に採用し、テーブル構成（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）を前提とした実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数の扱いについて注意点を明記:
  - 自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD の提供により、テスト時や CI／デプロイ時に意図しない環境読み込みを避けられる。

Notes / 既知の設計上の注意
- OpenAI API キーが未設定の場合（api_key 引数および OPENAI_API_KEY 環境変数両方未設定）では、score_news / score_regime は ValueError を送出します。呼び出し側で適切にキーを供給してください。
- DuckDB 側のテーブル存在とカラム型を前提とした実装になっているため、実行前にスキーマ準備（テーブル作成）が必要です。
- AI モジュールは JSON Mode（厳密な JSON レスポンス）を期待しますが、万が一のパース失敗や API エラー時はフェイルセーフとしてスコアをスキップまたは 0.0 にフォールバックする挙動になっています（例: 部分失敗時も他銘柄の既存スコアを保護する設計）。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装・統合テスト
- ETL の具体的なパイプライン実装（差分算出・品質チェックルール追加）
- モニタリングと自動リカバリの強化

--------------------------------
もし詳細な変更点（コミット単位や追加の設計方針）を反映したい場合は、該当するコミットログや追加情報を提供してください。README やリリースノートへの展開も支援します。