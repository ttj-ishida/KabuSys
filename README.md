# KabuSys

KabuSys は日本株向けの自動売買フレームワークのプロトタイプです。データ取得（data）、売買戦略（strategy）、注文実行（execution）、モニタリング（monitoring）という責務を分離したモジュール構成を採用しており、個別実装を差し替えながら自動売買ロジックを開発・検証できます。

バージョン: 0.1.0

---

## 主な機能

- モジュール化されたアーキテクチャ
  - data: 市場データの取得・加工を行うレイヤ
  - strategy: 売買シグナル生成を担うレイヤ
  - execution: 注文発行やブローカーAPIとのやり取りを行うレイヤ
  - monitoring: ログやメトリクス、稼働監視を行うレイヤ
- 最小限のコアパッケージ構成により、拡張や差し替えが容易
- テスト・開発しやすい src レイアウト

> 注: 本リポジトリは骨組み（スケルトン）実装です。各モジュールの詳細な実装は含まれていません。実運用では各レイヤでのエラーハンドリング、レート制限対応、セキュリティ対策（APIキー管理など）を適切に実装してください。

---

## 動作環境 / 前提

- Python 3.8 以上を推奨
- 外部ライブラリの指定はありません（実装に応じて requirements.txt を追加してください）

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <リポジトリURL>
cd <リポジトリディレクトリ>
```

2. 仮想環境を作成して有効化（推奨）
- Unix / macOS:
```
python3 -m venv .venv
source .venv/bin/activate
```
- Windows (PowerShell):
```
python -m venv .venv
.venv\Scripts\Activate.ps1
```

3. （任意）依存パッケージをインストール
- 依存ファイルがない場合は不要ですが、将来的には `requirements.txt` を追加して次のようにインストールします:
```
pip install -r requirements.txt
```

4. 開発モードでインストール（パッケージとして使う場合）
- プロジェクトに `pyproject.toml` / `setup.py` がある場合:
```
pip install -e .
```
- ない場合でも、ソースを直接参照して利用できます（例: PYTHONPATH を通す）。
```
PYTHONPATH=src python -c "import kabusys; print(kabusys.__version__)"
```

---

## 使い方（基本例）

現状はパッケージのスケルトンのみを提供しています。基本的なインポートとバージョン確認の例を示します。

Python REPL またはスクリプトで:
```
from kabusys import __version__, data, strategy, execution, monitoring

print("KabuSys version:", __version__)
print("modules:", data, strategy, execution, monitoring)
```

各モジュールは独自に実装してください。例として、簡易ワークフローの擬似コードを示します（実装は別途行う必要があります）:

```
# 擬似コード（実装例）
# 1. データ取得
market_data = data.fetch_historical(symbol="7203.T", period="1d", limit=100)

# 2. シグナル生成
signal = strategy.calculate_signal(market_data)

# 3. 注文実行
if signal == "BUY":
    execution.place_order(symbol="7203.T", side="BUY", qty=100)

# 4. モニタリング
monitoring.record_trade(...)
monitoring.emit_metrics(...)
```

各関数やクラスは現状定義されていないため、プロジェクトに合わせて実装してください。

---

## ディレクトリ構成

現在のソースツリーは以下の通りです。

```
.
├── src
│   └── kabusys
│       ├── __init__.py            # パッケージ情報 (version 等)
│       ├── data
│       │   └── __init__.py        # データ取得関連モジュール
│       ├── strategy
│       │   └── __init__.py        # 売買戦略関連モジュール
│       ├── execution
│       │   └── __init__.py        # 注文実行関連モジュール
│       └── monitoring
│           └── __init__.py        # モニタリング関連モジュール
└── README.md
```

- src/kabusys/__init__.py
  - パッケージ名、バージョン、エクスポート対象を定義しています（__version__ = "0.1.0"）。
- 各サブパッケージは現在スケルトン（空の __init__）です。実際の機能はこれらの中に実装してください。

---

## 開発ガイド / 推奨事項

- 各レイヤは単一責任を守る
  - data: API 呼び出し、データクレンジング、キャッシュ
  - strategy: シグナル生成、バックテスト用の純粋関数
  - execution: 注文の送信、注文状態の管理、再試行ロジック
  - monitoring: ロギング、メトリクス、アラート連携
- 設定や機密情報（API キー等）は環境変数やシークレット管理を使う
- テストを作成してCIで自動実行する
- ロギングと例外処理を充実させる（取引はクリティカルな操作です）

---

## 今後の作業例 / TODO

- 各モジュールに具体的な実装を追加（データプロバイダ / ブローカーAPI / 指標計算等）
- requirements.txt や pyproject.toml の整備
- ユニットテスト、統合テストの追加
- ドキュメント（API リファレンス、開発ガイド）

---

## ライセンス / 著作権

本リポジトリにライセンスファイルが含まれていない場合は、使用条件を明確にするために適切なライセンス（例: MIT, Apache-2.0 など）を追加してください。

---

ご希望があれば、README に以下を追加して作成します:
- 具体的な使用例（サンプル実装）の追加
- requirements.txt / pyproject.toml のテンプレート
- CI の設定サンプル（GitHub Actions 等）
どれを優先して追加しますか？