Keep a Changelogに準拠した形式で、このリポジトリの初期リリース用 CHANGELOG を以下に作成しました。
コードベースの内容から意図や設計方針を推測して記載しています。

CHANGELOG.md

---

# Changelog

すべての重要な変更をここに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

## [0.1.0] - 2026-03-29
初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期エクスポートを追加（__version__=0.1.0、data / research / ai 等を __all__ に含む）。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - export KEY=val 形式やクォート付き値、インラインコメントの取り扱いに対応するパーサ実装。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require 関数と Settings クラスを実装。
  - 環境（development / paper_trading / live）・ログレベルのバリデーション、各種パス (DUCKDB_PATH, SQLITE_PATH) のデフォルト値を定義。
- AI モジュール (src/kabusys/ai/)
  - ニュースセンチメント解析 (news_nlp.score_news)
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント（ai_score）を計算して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/コール）、各銘柄のトリミング（記事数・文字数制限）を実装。
    - JSON Mode レスポンスの堅牢なバリデーションとパース（余分な前後テキストから {} の抽出含む）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。
    - テスト用に内部の _call_openai_api をモック差し替え可能に設計。
    - タイムウィンドウ: JST 前日 15:00 〜 当日 08:30 を UTC に変換して利用（ルックアヘッド防止）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出・保存。
    - ma200 の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
    - マクロニュース抽出は定義済みキーワードでフィルタ、LLM 呼び出しは失敗時に 0.0 にフォールバックするフェイルセーフ実装。
    - OpenAI 呼び出しは専用の内部実装を持ち、テストで差し替え可能。
- データモジュール (src/kabusys/data/)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを基に営業日判定・次営業日/前営業日・期間内の営業日取得・SQ 日判定等のユーティリティを実装。
    - DB 登録がない場合は曜日ベース（土日を休業日）でフォールバックする一貫した挙動を保証。
    - カレンダー更新ジョブ (calendar_update_job) を実装し、J-Quants API からの差分取得・バックフィル・健全性チェックを行う（保存は idempotent 想定）。
  - ETL パイプライン (pipeline.py) と ETLResult の公開 (etl.py)
    - 差分取得・保存・品質チェック（quality モジュールと連携）を行う ETLResult データクラスを実装。
    - データ収集のバックフィル、最小データ開始日 (_MIN_DATA_DATE)、カレンダー先読み等の方針を実装。
    - DuckDB を用いた最大日付取得やテーブル存在チェック等のユーティリティ実装。
- リサーチ / ファクター (src/kabusys/research/)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR, 相対 ATR, 出来高指標）、Value（PER, ROE）などの計算関数を実装。prices_daily / raw_financials を参照。
    - データ不足時の None ハンドリング、SQL を用いた効率的なウィンドウ計算を実装。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、値→ランク変換、ファクター統計サマリー関数を実装。
    - IC 計算では同順位（ties）を平均ランクで処理、必要な有効レコード数が不足する場合は None を返す。
- パッケージ re-exports
  - kabusys.data.ETLResult を公開するインターフェースを用意。
  - research/__init__.py で主要関数を再エクスポート。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーや Slack トークン等の機密値は環境変数経由で管理し、設定がない場合は明示的にエラーを投げる箇所を実装（誤設定による静かなる失敗を防止）。

### 既知の制約・設計上の注意点 (Notes / Known issues)
- ルックアヘッドバイアス防止のため、全ての「対象日」ベース処理は datetime.today()/date.today() を直接参照しない設計。ただし calendar_update_job などは実行時に date.today() を利用する。
- API 呼び出しのフェイルセーフ: LLM 失敗時はゼロ値（中立）にフォールバックして処理を継続する設計（例: macro_sentiment=0.0、スコア収集失敗は該当銘柄をスキップ）。
- DuckDB の executemany に関する互換性（空リスト不可）を考慮して、INSERT/DELETE の前にパラメータ非空チェックを実装。
- OpenAI レスポンスの整形が破損している場合に備え、JSON 抽出や余分な前後テキストの回復処理を実装しているが、LLM 出力の不確実性は残る。
- news_nlp と regime_detector で内部の API 呼び出し関数を別実装にしている（モジュール間のプライベート関数共有を避けるため）。テスト時はそれぞれのモックポイントを差し替え可能。
- calendar の next/prev_trading_day は探索の最大幅を設定（_MAX_SEARCH_DAYS）して無限ループを防止。
- OpenAI モデルとして gpt-4o-mini を想定。将来のモデル変更に伴うレスポンス形式の変更に注意。

### 依存関係 (Dependencies)
- duckdb（データ処理・クエリ実行）
- openai（OpenAI の SDK を使用）
- 標準ライブラリ（datetime, json, logging, os, time 等）

---

今後のリリース案:
- ユニットテストの追加（ETL / AI モジュールのモックを用いた挙動検証）
- OpenAI レスポンススキーマのより厳密な型定義・カバレッジ向上
- jquants_client の実装詳細・エラー処理の拡張
- パフォーマンス最適化（大規模データにおける DuckDB クエリやバッチ戦略の改善）

---