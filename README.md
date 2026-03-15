# KabuSys

日本株自動売買システムの骨組み（雛形）です。モジュール化された構成で、データ取得、売買戦略、注文実行、監視をそれぞれ独立して実装できるようになっています。

現在のバージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を行うためのフレームワークの雛形です。機能ごとにパッケージを分離しており、以下の4つのコンポーネントを想定しています。

- data: 市場データの取得・整形（板情報、約定履歴、OHLCなど）
- strategy: 売買シグナル生成ロジック（エントリー／イグジット、資金管理）
- execution: 証券会社（例: kabu.com）のAPIへ注文を送る処理
- monitoring: ログ、メトリクス、アラート、実行状況の可視化

このリポジトリは基本的なパッケージ構造のみを含み、各モジュールはこれから実装して拡張していくことを想定しています。

---

## 機能一覧（想定・拡張ポイント）

現状は雛形のみですが、実装時に想定される機能は以下の通りです。

- データ取得
  - 株価（OHLC）、板情報、約定履歴の取得
  - CSV / データベースへの保存・読み込み
  - データの前処理（時間整列、欠損埋め）
- 戦略
  - 指標（移動平均、RSI 等）を用いたシグナル生成
  - リスク・資金管理（ポジションサイズ、最大ドローダウン制御）
  - バックテスト用のインターフェース
- 注文実行
  - 成行・指値注文の送信・訂正・キャンセル
  - 注文状態のポーリングとコールバック
  - 本番 / サンドボックス切替、APIキー管理
- 監視
  - ログ出力（ファイル・標準出力）
  - メトリクス（取引回数、勝率、P/L）
  - Slack/メール等へのアラート通知

---

## セットアップ手順

このリポジトリは src 配下にパッケージを置く構成です。実行するには Python 環境を用意し、`src` を Python のモジュール検索パスに含めてください。

1. リポジトリをクローン
   - git clone <repository-url>

2. Python 仮想環境の作成（推奨）
   - Unix/Mac:
     - python3 -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - まだ無い場合は、必要なパッケージ（例: requests, pandas 等）を手動で追加してください。
     - 例: pip install requests pandas

4. 実行方法（2通りの方法）
   - 方法A (簡易、開発中に推奨): PYTHONPATH に src を指定して実行
     - Unix/Mac:
       - PYTHONPATH=src python -c "import kabusys; print(kabusys.__version__)"
     - Windows (PowerShell):
       - $env:PYTHONPATH="src"; python -c "import kabusys; print(kabusys.__version__)"
   - 方法B (パッケージとしてインストールする場合): pyproject.toml / setup.cfg を追加してから
     - pip install -e .
     - その後通常のパッケージとして import 可能

5. 設定（APIキー等）
   - 実際に注文実行やデータ取得を行う場合は、証券会社の API キー等の設定が必要です。環境変数や設定ファイル（例: YAML, JSON）で取り扱うことを推奨します。

---

## 使い方（開発者向け簡易例）

現状は雛形パッケージなのでまずは動作確認と拡張ポイントの例を示します。

- パッケージのバージョン確認（動作確認）
  - PYTHONPATH=src python -c "import kabusys; print(kabusys.__version__)"

- モジュールの拡張例（擬似コード）
  - data モジュールにデータ取得関数を追加
    - src/kabusys/data/fetch.py を作成して market_data_fetch() を実装
  - strategy にシグナル生成クラスを追加
    - src/kabusys/strategy/simple_ma.py に SimpleMA を実装（short/long SMA でシグナル）
  - execution に注文送信ラッパーを追加
    - src/kabusys/execution/client.py に KabuClient を実装（send_order(), cancel_order() 等）
  - monitoring にログ・アラート機能を追加
    - src/kabusys/monitoring/logger.py 等

- 簡易ワークフロー（擬似コード）
  - データ取得 → 戦略でシグナル算出 → 注文発行 → 監視ログ記録

例（非常に簡略化した呼び出し例）:
- PYTHONPATH=src python - <<'PY'
  from kabusys import data, strategy, execution, monitoring
  # 実装したモジュールを呼び出して利用する
  PY

（各モジュールはまだ未実装のため、実際の呼び出しは各自で実装後に行ってください）

---

## ディレクトリ構成

現在の最小構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - data/
      - __init__.py
      - (データ取得ロジックをここに追加)
    - strategy/
      - __init__.py
      - (戦略ロジックをここに追加)
    - execution/
      - __init__.py
      - (注文実行ロジックをここに追加)
    - monitoring/
      - __init__.py
      - (監視・ロギング関連をここに追加)

ファイル例（現状）:
- src/kabusys/__init__.py
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

---

## 開発のヒント・推奨事項

- モジュールの責務を明確に分ける（単一責任原則）
- テストを書いてから実装する（pytest を推奨）
- 設定や認証情報はコードにハードコーディングせず、環境変数や外部設定ファイルで管理する
- 実際の注文執行ロジックはサンドボックス環境で十分に検証する（誤発注リスク回避）
- ロギングを充実させ、事後解析ができるようにする（トレードログ、注文履歴、エラートレース）

---

必要であれば、pyproject.toml / setup.cfg のテンプレート、サンプル戦略の雛形、API クライアントのサンプル実装、CI（GitHub Actions）設定等も用意します。どれを優先して追加したいか教えてください。